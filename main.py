from trade_client import *
from store_order import *
from logger import logger
from load_config import *
from new_listings_scraper import *
from send_sms import *


from collections import defaultdict
from datetime import datetime, time
import time
import threading

import json
from json import JSONEncoder

import os.path
import sys, os

old_coins = ["CHESS", "OTHERCRAP"]

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

    if not test_mode:
        logger.info(f'!!! LIVE MODE !!!')

    t = threading.Thread(target=search_and_update)
    t.start()

    t2 = threading.Thread(target=get_all_currencies)
    t2.start()

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
                    volume = order[coin]['volume']
                    stored_price = float(order[coin]['price'])
                    symbol = order[coin]['symbol']
                
                top_position_price = stored_price + (stored_price*coin_tp /100)

                #logger.info(f"Data for sell: {coin=},  {stored_price=}, {coin_tp=}, {coin_sl=}, {volume=}, {symbol=}")
				
                #logger.info(f"get_last_price existing coin: {coin}")
                last_price = get_last_price(symbol, pairing)
                #logger.info("Finished get_last_price")

                stop_loss_price = stored_price + (stored_price*coin_sl /100)

                logger.info(f'{last_price=}\t[BUY: ${"{:,.2f}".format(stored_price)} (+/-): {"{:,.2f}".format(((float(last_price) - stored_price) / stored_price) * 100)}%]\t[TOP: ${"{:,.2f}".format(top_position_price)} or {"{:,.2f}".format(coin_tp)}%]')
                logger.info(f'{stop_loss_price=}  \t{"{:,.2f}".format(coin_sl)}%')

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

                    logger.info(f'updated tp: {round(new_tp, 3)}% / ${"{:,.2f}".format(new_top_position_price)}')
                    logger.info(f'updated sl: {round(new_sl, 3)}% / ${"{:,.2f}".format(new_stop_loss_price)}')

                # close trade if tsl is reached or trail option is not enabled
                elif float(last_price) < stored_price + (
                        stored_price * coin_sl / 100) or float(last_price) > stored_price + (
                        stored_price * coin_tp / 100) and not enable_tsl:
                    try:
                        # sell for real if test mode is set to false
                        if not test_mode:
                            logger.info(f'starting sell place_order with :{symbol} | {pairing} | {float(volume)*float(last_price)} | side=sell {last_price}')
                            sell = place_order(symbol, pairing, float(volume)*float(last_price), 'sell', last_price)
                            logger.info("Finish sell place_order")

                        sold_message = f'sold {coin} with {(float(last_price) - stored_price) / float(stored_price)*100}% PNL'
                        logger.info(sold_message)

                        if not test_mode:
                            send_sms_message(sold_message)

                        # remove order from json file
                        order.pop(coin)
                        store_order('order.json', order)
                        logger.debug('Order saved in order.json')

                    except Exception as e:
                        logger.error(e)

                    # store sold trades data
                    else:
                        if not test_mode:
                            sold_coins[coin] = sell
                            sold_coins[coin] = sell.__dict__
                            sold_coins[coin].pop("local_vars_configuration")

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
                                'price': last_price}
                            
                            logger.info(f'Sold coins:\r\n {sold_coins[coin]}')

                            store_order('sold.json', sold_coins)

        # the buy block and logic pass
        # announcement_coin = load_order('new_listing.json')
        if os.path.isfile('new_listing.json'):
            announcement_coin = load_order('new_listing.json')
        else:
            announcement_coin = False

        global supported_currencies

        if announcement_coin and announcement_coin not in order and announcement_coin not in sold_coins and announcement_coin not in old_coins:
            logger.info(f'New annoucement detected: {announcement_coin}')

            if supported_currencies is not False:
                if announcement_coin in supported_currencies:
                    logger.debug("Starting get_last_price")
                    price = get_last_price(announcement_coin, pairing)

                    logger.debug(f"Coin price: { price}")
                    logger.debug('Finished get_last_price')

                    try:
                        # Run a test trade if true
                        if config['TRADE_OPTIONS']['TEST']:
                            order[announcement_coin] = {
                                'symbol': announcement_coin,
                                'price': price,
                                'volume': qty,
                                'time': datetime.timestamp(datetime.now()),
                                'tp': tp,
                                'sl': sl,
                                'id': 'test-order',
                                'text': 'test-order',
                                'create_time': datetime.timestamp(datetime.now()),
                                'update_time': datetime.timestamp(datetime.now()),
                                'currency_pair': f'{announcement_coin}_{pairing}',
                                'status': 'filled',
                                'type': 'limit',
                                'account': 'spot',
                                'side': 'buy',
                                'iceberg': '0'
                            }
                            logger.info('PLACING TEST ORDER')
                            logger.info(order[announcement_coin])
                        # place a live order if False
                        else:
                            logger.info(f'starting buy place_order with : {announcement_coin=} | {pairing=} | {qty=} | side = buy | {price=}')
                            order[announcement_coin] = place_order(announcement_coin, pairing, qty,'buy', price)
                            order[announcement_coin] = order[announcement_coin].__dict__
                            order[announcement_coin].pop("local_vars_configuration")
                            order[announcement_coin]['tp'] = tp
                            order[announcement_coin]['sl'] = sl
                            logger.info('Finished buy place_order')

                    except Exception as e:
                        logger.error(e)

                    else:
                        message = f'Order created with {qty} on {announcement_coin} at a price of {price} each'
                        logger.info(message)
                        
                        if not test_mode:
                            send_sms_message(message)

                        store_order('order.json', order)
                        
                else:
                    logger.warning(f'{announcement_coin=} is not supported on gate io')
                    os.remove("new_listing.json")
                    logger.debug('Removed new_listing.json due to coin not being '
                                  'listed on gate io')
            else:
                get_all_currencies()
        #else:
        #    logger.info( 'No coins announced, or coin has already been bought/sold. Checking more frequently in case TP and SL need updating')

        time.sleep(3)
        # except Exception as e:
        # print(e)


if __name__ == '__main__':
    logger.info('working...')
    main()