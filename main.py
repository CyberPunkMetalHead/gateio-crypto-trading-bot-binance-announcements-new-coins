from trade_client import *
from store_order import *
from logger import logger
from load_config import *
from new_listings_scraper import *
from send_sms import *
import globals

from collections import defaultdict
from datetime import datetime, time
import time
import threading
import copy

import json
from json import JSONEncoder

import os.path
import sys, os

old_coins = ["MOVR", "BNX", "SAND"]

# loads local configuration
config = load_config('config.yml')

# load necessary files
if os.path.isfile('sold.json'):
    sold_coins = load_order('sold.json')
else:
    sold_coins = {}

if os.path.isfile('order.json'):
    order = load_order('order.json')
else:
    order = {}

if os.path.isfile('new_listing.json'):
    announcement_coin = load_order('new_listing.json')
else:
    announcement_coin = False



# Keep the supported currencies loaded in RAM so no time is wasted fetching
# currencies.json from disk when an announcement is made
global supported_currencies


logger.debug("Starting get_all_currencies")
supported_currencies = get_all_currencies(single=True)
logger.debug("Finished get_all_currencies")


global new_listings

# load necessary files
if os.path.isfile('newly_listed.json'):
    newly_listed = get_new_listings('newly_listed.json')
    new_listings = [c for c in list(newly_listed) if c not in order and c not in sold_coins]
    if announcement_coin:
        new_listings = [c for c in list(newly_listed) if c not in announcement_coin]
else:
    new_listings = {}


def main():
    """
    Sells, adjusts TP and SL according to trailing values
    and buys new coins
    """
    # store config deets
    tp = config['TRADE_OPTIONS']['TP']
    sl = config['TRADE_OPTIONS']['SL']
    enable_tsl = config['TRADE_OPTIONS']['ENABLE_TSL']
    tsl = config['TRADE_OPTIONS']['TSL']
    ttp = config['TRADE_OPTIONS']['TTP']
    pairing = config['TRADE_OPTIONS']['PAIRING']
    test_mode = config['TRADE_OPTIONS']['TEST']
    enable_sms = config['TRADE_OPTIONS']['ENABLE_SMS']
    
    globals.stop_threads = False
    
    session = {}
    
    if not test_mode:
        logger.info(f'!!! LIVE MODE !!!')
        if(enable_sms):
            logger.info('!!! SMS Enabled on Buy/Sell !!!')

    t1 = threading.Thread(target=search_gateio_and_update, args=[pairing, new_listings])
    t1.start()

    t2 = threading.Thread(target=search_binance_and_update, args=[pairing,])
    t2.start()

    t3 = threading.Thread(target=get_all_currencies)
    t3.start()

    try:
        while True:
            # check if the order file exists and load the current orders
            # basically the sell block and update TP and SL logic
            if len(order) > 0:
                for coin in list(order):
                    
                    if float(order[coin]['_tp']) == 0:
                        st = order[coin]['_status']
                        logger.info(f"Order is initialized but not ready | Status={st}")
                        continue

                    # store some necessary trade info for a sell
                    coin_tp = order[coin]['_tp']
                    coin_sl = order[coin]['_sl']
                    
                    volume = order[coin]['_amount']
                    stored_price = float(order[coin]['_price'])
                    symbol = order[coin]['_fee_currency']

                    if float(stored_price) == 0:
                        continue #avoid div by zero error

                    top_position_price = stored_price + (stored_price*coin_tp /100)

                    #logger.info(f"Data for sell: {coin=},  {stored_price=}, {coin_tp=}, {coin_sl=}, {volume=}, {symbol=}")
                    
                    #logger.info(f"get_last_price existing coin: {coin}")
                    obj = get_last_price(symbol, pairing, False)
                    last_price = obj.last
                    #logger.info("Finished get_last_price")

                    stop_loss_price = stored_price + (stored_price*coin_sl /100)

                    logger.info(f'{symbol=}-{last_price=}\t[STOP: ${"{:,.5f}".format(stop_loss_price)} or {"{:,.2f}".format(coin_sl)}%]\t[TOP: ${"{:,.5f}".format(top_position_price)} or {"{:,.2f}".format(coin_tp)}%]\t[BUY: ${"{:,.5f}".format(stored_price)} (+/-): {"{:,.2f}".format(((float(last_price) - stored_price) / stored_price) * 100)}%]')

                    if float(last_price) == 0:
                        continue # need positive price / do not place buy order 

                    # update stop loss and take profit values if threshold is reached
                    if float(last_price) > stored_price + (
                            stored_price * coin_tp / 100) and enable_tsl:
                        # increase as absolute value for TP
                        new_tp = float(last_price) + (float(last_price) * ttp / 100)
                        # convert back into % difference from when the coin was bought
                        new_tp = float((new_tp - stored_price) / stored_price * 100)

                        # same deal as above, only applied to trailing SL
                        new_sl = float(last_price) + (float(last_price)*tsl / 100)
                        new_sl = float((new_sl - stored_price) / stored_price * 100)

                        # new values to be added to the json file
                        order[coin]['_tp'] = new_tp
                        order[coin]['_sl'] = new_sl
                        store_order('order.json', order)

                        new_top_position_price = stored_price + (stored_price*new_tp /100)
                        new_stop_loss_price = stored_price + (stored_price*new_sl /100)

                        logger.info(f'updated tp: {round(new_tp, 3)}% / ${"{:,.3f}".format(new_top_position_price)}')
                        logger.info(f'updated sl: {round(new_sl, 3)}% / ${"{:,.3f}".format(new_stop_loss_price)}')

                    # close trade if tsl is reached or trail option is not enabled
                    elif float(last_price) < stored_price + (
                            stored_price * coin_sl / 100) or float(last_price) > stored_price + (
                            stored_price * coin_tp / 100) and not enable_tsl:
                        try:
                            fees = float(order[coin]['_fee'])
                            sell_volume_adjusted = float(volume) - fees

                            logger.info(f'starting sell place_order with :{symbol} | {pairing} | {volume} | {sell_volume_adjusted} | {fees} | {float(sell_volume_adjusted)*float(last_price)} | side=sell | last={last_price}')

                            # sell for real if test mode is set to false
                            if not test_mode:
                                sell = place_order(symbol, pairing, float(sell_volume_adjusted)*float(last_price), 'sell', last_price)

                                #check for completed sell order
                                if sell._status != 'closed':
                                    # cancel sell order
                                    if sell._status == "open":
                                        cancel_open_order(sell._id, coin, pairing)

                                    # change order to sell remaing
                                    if float(sell._left) > 0 and float(sell._amount) > float(sell._left):
                                        # adjust down order _amount and _fee
                                        order[coin]['_amount'] = sell._left
                                        order[coin]['_fee'] = f'{fees - (float(sell._fee) / float(sell._price))}'
                                    
                                        # add sell order sold.json (handled better in session.json now)
                                        id = f"{coin}_{id}"
                                        sold_coins[id] = sell
                                        sold_coins[id] = sell.__dict__
                                        sold_coins[id].pop("local_vars_configuration")
                                        logger.info(f"Sell order did not close! {sell._left} of {coin} remaining. Adjusted order _amount and _fee to perform sell of remaining balance")

                                        # add to session orders
                                        try:
                                            if len(session) > 0:
                                                dp = copy.deepcopy(sold_coins[id])
                                                session[coin]['orders'].append(dp)
                                        except Exception as e:
                                            print(e)
                                        pass
                                    
                                    # keep going.  Not finished until status is 'closed'
                                    continue
                                
                                logger.debug(f"Finish sell place_order {sell}")
                                


                            sold_message = f'sold {coin} with {round((float(last_price) - stored_price) * float(volume), 3)} profit | {round((float(last_price) - stored_price) / float(stored_price)*100, 3)}% PNL'
                            logger.info(sold_message)

                            # remove order from json file
                            order.pop(coin)
                            store_order('order.json', order)
                            logger.debug('Order saved in order.json')
                            
                            if not test_mode and enable_sms:
                                try:
                                    send_sms_message(sold_message)
                                except Exception:
                                    pass

                        except Exception as e:
                            logger.error(e)

                        # store sold trades data
                        else:
                            if not test_mode:
                                sold_coins[coin] = sell
                                sold_coins[coin] = sell.__dict__
                                sold_coins[coin].pop("local_vars_configuration")
                                sold_coins[coin]['profit'] = f'{float(last_price) - stored_price}'
                                sold_coins[coin]['relative_profit_%'] = f'{(float(last_price) - stored_price) / stored_price * 100}%'

                                
                                # add to session orders
                                try: 
                                    if len(session) > 0:
                                        dp = copy.deepcopy(sold_coins[coin])
                                        session[coin]['orders'].append(dp)
                                except Exception as e:
                                    print(e)
                                    pass
                            else:
                                sold_coins[coin] = {
                                    'symbol': coin,
                                    'price': last_price,
                                    'volume': volume,
                                    'time': datetime.timestamp(datetime.now()),
                                    'profit': f'{float(last_price) - stored_price}',
                                    'relative_profit_%': f'{(float(last_price) - stored_price) / stored_price * 100}%',
                                    'id': 'test-order',
                                    'text': 'test-order',
                                    'create_time': datetime.timestamp(datetime.now()),
                                    'update_time': datetime.timestamp(datetime.now()),
                                    'currency_pair': f'{symbol}_{pairing}',
                                    'status': 'closed',
                                    'type': 'limit',
                                    'account': 'spot',
                                    'side': 'sell',
                                    'iceberg': '0',
                                    'price': last_price
                                    }
                                
                                logger.info(f'Sold coins:\r\n {sold_coins[coin]}')

                               
                            store_order('sold.json', sold_coins)
                            logger.info('Order saved in sold.json')
                                
                            if len(session) > 0:
                                store_order('session.json', session)
                                logger.debug('Session saved in session.json')

            # the buy block and logic pass
            # announcement_coin = load_order('new_listing.json')
            if os.path.isfile('new_listing.json'):
                announcement_coin = load_order('new_listing.json')
                if(len(announcement_coin) > 0):
                    if(len(order) > 0):
                        announcement_coin = [c for c in announcement_coin if c not in order]
                    
                    if(len(announcement_coin) > 0):
                        announcement_coin = [c for c in announcement_coin if c not in old_coins and c not in sold_coins]
                    
                    if(len(announcement_coin) > 0):
                        announcement_coin = announcement_coin[0]
                    else:
                        announcement_coin = False
                else:
                    announcement_coin = False
            else:
                announcement_coin = False

            global supported_currencies

            if announcement_coin and announcement_coin not in order and announcement_coin not in sold_coins and announcement_coin not in old_coins:
                logger.debug(f'New annoucement detected: {announcement_coin}')

                if supported_currencies is not False:
                    if announcement_coin in supported_currencies:
                        
                        # get latest price object
                        obj = get_last_price(announcement_coin, pairing, False)
                        price = obj.last

                        if float(price) == 0:
                            continue # wait for positive price

                        volume = config['TRADE_OPTIONS']['QUANTITY']
                        
                        if announcement_coin not in session:
                            session[announcement_coin] = {}
                            session[announcement_coin].update({'total_volume': 0})
                            session[announcement_coin].update({'total_amount': 0})
                            session[announcement_coin].update({'total_fees': 0})
                            session[announcement_coin]['orders'] = list()
                        
                        # initalize order object
                        if announcement_coin not in order:
                            order[announcement_coin] = {}
                            order[announcement_coin]['_amount'] = f'{volume / float(price)}'
                            order[announcement_coin]['_left'] = f'{volume / float(price)}'
                            order[announcement_coin]['_fee'] = f'{0}'
                            order[announcement_coin]['_tp'] = f'{0}'
                            order[announcement_coin]['_sl'] = f'{0}'
                            order[announcement_coin]['_status'] = 'unknown'
                            if announcement_coin in session:
                                if len(session[announcement_coin]['orders']) == 0:
                                    order[announcement_coin]['_status'] = 'test_partial_fill_order'
                                else:
                                    order[announcement_coin]['_status'] = 'cancelled'

                        amount = float(order[announcement_coin]['_amount'])
                        left = float(order[announcement_coin]['_left'])
                        status = order[announcement_coin]['_status']
                        volume = volume - session[announcement_coin]['total_volume']

                        if left - amount != 0:
                            # partial fill. 
                            amount = left
                        
                        logger.info(f'starting buy place_order with : {announcement_coin=} | {pairing=} | {volume=} | {amount=} x {price=} | side = buy | {status=}')

                        try:
                            # Run a test trade if true
                            if config['TRADE_OPTIONS']['TEST']:
                                
                                if order[announcement_coin]['_status'] == 'cancelled':
                                    status = 'closed'
                                    left = 0
                                    fee = f'{float(amount) * .02}'
                                else:
                                    status = 'cancelled'
                                    left = f'{amount *.66}'
                                    fee = f'{float(amount - float(left)) * .02}'

                                order[announcement_coin] = {
                                    '_fee_currency': announcement_coin,
                                    '_price': f'{price}',
                                    '_amount': f'{amount}',
                                    '_time': datetime.timestamp(datetime.now()),
                                    '_tp': tp,
                                    '_sl': sl,
                                    '_ttp': ttp,
                                    '_tsl': tsl,
                                    '_id': 'test-order',
                                    '_text': 'test-order',
                                    '_create_time': datetime.timestamp(datetime.now()),
                                    '_update_time': datetime.timestamp(datetime.now()),
                                    '_currency_pair': f'{announcement_coin}_{pairing}',
                                    '_status': status,
                                    '_type': 'limit',
                                    '_account': 'spot',
                                    '_side': 'buy',
                                    '_iceberg': '0',
                                    '_left': f'{left}',
                                    '_fee': fee
                                }
                                logger.info('PLACING TEST ORDER')
                                logger.info(order[announcement_coin])
                            # place a live order if False
                            else:
                                # just in case...stop buying more than our config amount
                                assert amount * float(price) <= float(volume)

                                order[announcement_coin] = place_order(announcement_coin, pairing, volume,'buy', price)
                                order[announcement_coin] = order[announcement_coin].__dict__
                                order[announcement_coin].pop("local_vars_configuration")
                                order[announcement_coin]['_tp'] = tp
                                order[announcement_coin]['_sl'] = sl
                                order[announcement_coin]['_ttp'] = ttp
                                order[announcement_coin]['_tsl'] = tsl
                                logger.debug('Finished buy place_order')

                        except Exception as e:
                            logger.error(e)

                        else:
                            order_status = order[announcement_coin]['_status']

                            message = f'Order created on {announcement_coin} at a price of {price} each.  {order_status=}'
                            logger.info(message)
                            

                            if order_status == "closed":
                                order[announcement_coin]['_amount_filled'] = order[announcement_coin]['_amount']
                                session[announcement_coin]['total_volume'] = session[announcement_coin]['total_volume'] + (float(order[announcement_coin]['_amount']) * float(order[announcement_coin]['_price']))
                                session[announcement_coin]['total_amount'] = session[announcement_coin]['total_amount'] + float(order[announcement_coin]['_amount'])
                                session[announcement_coin]['total_fees'] = session[announcement_coin]['total_fees'] + float(order[announcement_coin]['_fee'])
                                session[announcement_coin]['orders'].append(copy.deepcopy(order[announcement_coin]))

                                # update order to sum all amounts and all fees
                                # this will set up our sell order for sale of all filled buy orders
                                tf = session[announcement_coin]['total_fees']
                                ta = session[announcement_coin]['total_amount']
                                order[announcement_coin]['_fee'] = f'{tf}'
                                order[announcement_coin]['_amount'] = f'{ta}'

                                store_order('order.json', order)
                                store_order('session.json', session)
                                
                                if not test_mode and enable_sms:
                                    try:
                                        send_sms_message(message)
                                    except Exception:
                                        pass
                            else:
                                if not test_mode and order_status == 'open':
                                    # cancel orders and try again in the next iteration
                                    cancel_open_order(order[announcement_coin]['_id'], announcement_coin, pairing)
                                    logger.info(f"Cancelled order {order[announcement_coin]['_id']} .  Waiting for status of 'closed' for {announcement_coin}")
                                
                                if order_status == "cancelled" and float(order[announcement_coin]['_amount']) > float(order[announcement_coin]['_left']) and float(order[announcement_coin]['_left']) > 0:
                                    # partial order. Change qty and fee_total
                                    partial_amount = float(order[announcement_coin]['_amount']) - float(order[announcement_coin]['_left'])
                                    partial_fee = float(order[announcement_coin]['_fee'])
                                    order[announcement_coin]['_amount_filled'] = f'{partial_amount}'
                                    session[announcement_coin]['total_volume'] = session[announcement_coin]['total_volume'] + (partial_amount * float(order[announcement_coin]['_price']))
                                    session[announcement_coin]['total_amount'] = session[announcement_coin]['total_amount'] + partial_amount
                                    session[announcement_coin]['total_fees'] = session[announcement_coin]['total_fees'] + partial_fee

                                    session[announcement_coin]['orders'].append(copy.deepcopy(order[announcement_coin]))
                                    logger.info(f"Parial fill order detected.  {order_status=} | {partial_amount=} out of {amount=} | {partial_fee=} | {price=}")

                                logger.info(f"clearing order with a status of {order_status}.  Waiting for 'closed' status")
                                order.clear()  # reset for next iteration
                        
                            
                    else:
                        logger.warning(f'{announcement_coin=} is not supported on gate io')
                        if os.path.isfile('new_listing.json'):
                            os.remove("new_listing.json")
                        logger.debug('Removed new_listing.json due to coin not being '
                                    'listed on gate io')
                else:
                    get_all_currencies()
            #else:
            #    logger.info( 'No coins announced, or coin has already been bought/sold. Checking more frequently in case TP and SL need updating')

            time.sleep(1)
            # except Exception as e:
            # print(e)
    except KeyboardInterrupt:
        logger.info('Stopping Threads')
        globals.stop_threads = True
        t1.join()
        t2.join()
        t3.join()


if __name__ == '__main__':
    logger.info('working...')
    main()