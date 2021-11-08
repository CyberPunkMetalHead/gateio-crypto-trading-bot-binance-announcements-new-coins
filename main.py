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

import json
from json import JSONEncoder

import os.path
import sys, os

old_coins = ["RGT"]

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
    qty = config['TRADE_OPTIONS']['QUANTITY']
    test_mode = config['TRADE_OPTIONS']['TEST']
    enable_sms = config['TRADE_OPTIONS']['ENABLE_SMS']
    
    max_qty = qty
    globals.stop_threads = False
    
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

    while True:
        # check if the order file exists and load the current orders
        # basically the sell block and update TP and SL logic
        if len(order) > 0:
            for coin in list(order):
                
                # store some necessary trade info for a sell
                coin_tp = order[coin]['tp']
                coin_sl = order[coin]['sl']
                
                if not test_mode:
                    volume = order[coin]['_amount']
                    stored_price = float(order[coin]['_price'])
                    symbol = order[coin]['_fee_currency']
                else:
    try:
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

                logger.info(f'{symbol=}-{last_price=}\t[BUY: ${"{:,.2f}".format(stored_price)} x {volume} (+/-): {"{:,.2f}".format(((float(last_price) - stored_price) / stored_price) * 100)}%]\t[TOP: ${"{:,.2f}".format(top_position_price)} or {"{:,.2f}".format(coin_tp)}%]')
                logger.info(f'{symbol=}-{stop_loss_price=}  \t{"{:,.2f}".format(coin_sl)}%')

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
                    order[coin]['tp'] = new_tp
                    order[coin]['sl'] = new_sl
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

                        logger.info(f'starting sell place_order with :{symbol} | {pairing} | {volume} | {float(volume)*float(last_price)} | side=sell | last={last_price}')                        

                        # sell for real if test mode is set to false
                        if not test_mode:
                            sell = place_order(symbol, pairing, float(volume)*float(last_price), 'sell', last_price)

                            #check for completed sell order
                            if sell._status != 'closed':
                                # cancel sell order
                                if sell._status == "open":
                                    cancel_open_order(sell._id, coin, pairing)

                                # change order to sell remaing
                                if float(sell._left) > 0 and float(sell._amount) > float(sell._left):
                                    order[coin]['_amount'] = sell._left
                                
                                    # store sell order in whatever state as "coin_id" if any 
                                    id = f"{coin}_{id}"
                                    sold_coins[id] = sell
                                    sold_coins[id] = sell.__dict__
                                    sold_coins[id].pop("local_vars_configuration")
                                    logger.info(f"Sell order did not close! {sell._left} remaining. Perform sell again")
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
                            sold_coins[coin]['profit'] = float(last_price) - stored_price
                            sold_coins[coin]['relative_profit_%'] = round((float(
                                    last_price) - stored_price) / stored_price * 100, 3)

                            store_order('sold.json', sold_coins)
                            logger.info('Order saved in sold.json')
                        else:
                            sold_coins[coin] = {
                                'symbol': coin,
                                'price': last_price,
                                'volume': volume,
                                'time': datetime.timestamp(datetime.now()),
                                'profit': float(last_price) - stored_price,
                                'relative_profit_%': round((float(
                                    last_price) - stored_price) / stored_price * 100, 3),
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

                    if float(qty) == 0:
                        old_coins.append(announcement_coin)
                        continue # hit our order total
                    
                    logger.info(f'starting buy place_order with : {announcement_coin=} | {pairing=} | {qty=} | side = buy | {price=}')

                    try:
                        # Run a test trade if true
                        if config['TRADE_OPTIONS']['TEST']:
                            
                            left = 0
                            if max_qty == qty:
                                left = float(qty) / 2
                                

                            order[announcement_coin] = {
                                'symbol': announcement_coin,
                                '_fee_currency': announcement_coin,
                                'price': price,
                                '_price': price,
                                '_amount': qty,
                                'time': datetime.timestamp(datetime.now()),
                                'tp': tp,
                                'sl': sl,
                                'ttp': ttp,
                                'tsl': tsl,
                                'id': 'test-order',
                                '_id': 'test-order',
                                'text': 'test-order',
                                'create_time': datetime.timestamp(datetime.now()),
                                'update_time': datetime.timestamp(datetime.now()),
                                'currency_pair': f'{announcement_coin}_{pairing}',
                                'status': 'filled',
                                '_status': 'filled',
                                'type': 'limit',
                                '_type': 'limit',
                                'account': 'spot',
                                '_account': 'spot',
                                'side': 'buy',
                                '_side': 'buy',
                                'iceberg': '0',
                                'left': str(left),
                                '_left': str(left),
                                '_fee': str(float(qty) * float(price) * .03)
                            }
                            logger.info('PLACING TEST ORDER')
                            logger.info(order[announcement_coin])
                        # place a live order if False
                        else:
                            order[announcement_coin] = place_order(announcement_coin, pairing, qty,'buy', price)
                            order[announcement_coin] = order[announcement_coin].__dict__
                            order[announcement_coin].pop("local_vars_configuration")
                            order[announcement_coin]['tp'] = tp
                            order[announcement_coin]['sl'] = sl
                            order[announcement_coin]['symbol'] = announcement_coin
                            logger.debug('Finished buy place_order')

                    except Exception as e:
                        logger.error(e)

                    else:
                        if test_mode:
                            order_status = order[announcement_coin]['status']
                        else:
                            order_status = order[announcement_coin]['_status']

                        message = f'Order created on {announcement_coin} at a price of {price} each.  {order_status=}'
                        logger.info(message)
                        

                        if order_status == 'filled' or order_status == "closed":
                            if test_mode and float(order[announcement_coin]['_left']) > 0 and float(order[announcement_coin]['_amount']) > float(order[announcement_coin]['_left']):
                                # you can only sell what you have. Minus fees.  Look for unfulfilled
                                newAmount = float(order[announcement_coin]['_amount']) - float(order[announcement_coin]['_left']) - float(order[announcement_coin]['_fee'])
                                order[announcement_coin]['volume'] = newAmount
                            else:
                                store_order('order_fulfilled.json', order)

                                # you can only sell what you have. Minus fees.  Look for unfulfilled
                                newAmount = float(order[announcement_coin]['_amount']) - float(order[announcement_coin]['_left']) - float(order[announcement_coin]['_fee'])
                                order[announcement_coin]['_amount'] = newAmount

                            store_order('order.json', order)
                            
                            if not test_mode and enable_sms:
                                try:
                                    send_sms_message(message)
                                except Exception:
                                    pass
                        elif order_status == 'open' or order_status == 'cancelled':
                            if not test_mode and order_status == 'open':
                                # cancel orders and try again in the next iteration
                                cancel_open_order(order[announcement_coin]['_id'], announcement_coin, pairing)
                                logger.info(f"Cancelled order {order[announcement_coin]['_id']} .  Waiting for status of 'filled/closed' for {announcement_coin}")
                            
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