from trade_client import *
from store_order import *
from logger import logger
from load_config import *
from new_listings_scraper import *
import globals

from collections import defaultdict
from datetime import datetime, time
import time
import threading

import json
from json import JSONEncoder

import os.path
import sys, os

old_coins = ["OTHERCRAP"]

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
    ath = config['TRADE_OPTIONS']['24H']
    enable_tsl = config['TRADE_OPTIONS']['ENABLE_TSL']
    tsl = config['TRADE_OPTIONS']['TSL']
    ttp = config['TRADE_OPTIONS']['TTP']
    pairing = config['TRADE_OPTIONS']['PAIRING']
    qty = config['TRADE_OPTIONS']['QUANTITY']
    test_mode = config['TRADE_OPTIONS']['TEST']

    globals.stop_threads = False

    t = threading.Thread(target=search_and_update)
    t.start()

    t2 = threading.Thread(target=get_all_currencies)
    t2.start()

    try:
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

                    logger.debug(f'Data for sell: {coin=} | {stored_price=} | {coin_tp=} | {coin_sl=} | {volume=} | {symbol=} ')

                    logger.info(f'get_coin_info existing coin: {coin}')
                    coin_info = get_coin_info(symbol, pairing)

                    logger.info("Finished get_coin_info")
                    logger.info(f'{coin_info.last=}')
                    logger.info(f'{stored_price + (stored_price*sl /100)=}')

                    # update stop loss and take profit values if threshold is reached
                    if float(coin_info.last) > stored_price + (
                            stored_price * coin_tp / 100) and enable_tsl:
                        # increase as absolute value for TP
                        new_tp = float(coin_info.last) + (float(coin_info.last) * ttp / 100)
                        # convert back into % difference from when the coin was bought
                        new_tp = float((new_tp - stored_price) / stored_price * 100)

                        # same deal as above, only applied to trailing SL
                        new_sl = float(coin_info.last) + (float(coin_info.last)*tsl / 100)
                        new_sl = float((new_sl - stored_price) / stored_price * 100)

                        # new values to be added to the json file
                        order[coin]['tp'] = new_tp
                        order[coin]['sl'] = new_sl
                        store_order('order.json', order)

                        logger.info(f'Updated TP: {round(new_tp, 3)} and SL:'
                                     f' {round(new_sl, 3)}')

                    # close trade if tsl is reached or trail option is not enabled
                    elif float(coin_info.last) < stored_price + (
                            stored_price * coin_sl / 100) or float(coin_info.last) > stored_price + (
                            stored_price * coin_tp / 100) and not enable_tsl:
                        try:
                            # sell for real if test mode is set to false
                            if not test_mode:
                                logger.info(f'starting sell place_order with :{symbol} | {pairing} | {float(volume)*float(coin_info.last)} | side=sell {coin_info.last}')
                                sell = place_order(symbol, pairing, float(volume)*float(coin_info.last), 'sell', coin_info.last)
                                logger.info("Finish sell place_order")
                            logger.info(f'sold {coin} with {(float(coin_info.last) - stored_price) / float(stored_price)*100}% PNL')

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
                                    'price': coin_info.last,
                                    'volume': volume,
                                    'time': datetime.timestamp(datetime.now()),
                                    'profit': float(coin_info.last) - stored_price,
                                    'relative_profit_%': round((float(
                                        coin_info.last) - stored_price) / stored_price * 100, 3),
                                    'id': 'test-order',
                                    'text': 'test-order',
                                    'create_time': datetime.timestamp(datetime.now()),
                                    'update_time': datetime.timestamp(datetime.now()),
                                    'currency_pair': f'{symbol}_{pairing}',
                                    'status': 'closed',
                                    'type': 'limit',
                                    'account': 'spot',
                                    'side': 'sell',
                                    'iceberg': '0'}
                                logger.info('Sold coins:' + str(sold_coins[coin]))

                                store_order('sold.json', sold_coins)

            # the buy block and logic pass
            # announcement_coin = load_order('new_listing.json')
            if os.path.isfile('new_listing.json'):
                announcement_coin = load_order('new_listing.json')
            else:
                announcement_coin = False

            global supported_currencies

            if announcement_coin and announcement_coin not in order and announcement_coin not in sold_coins and announcement_coin not in old_coins:
                logger.info(f'New announcement detected: {announcement_coin}')
                if not supported_currencies:
                    supported_currencies = get_all_currencies(single=True)
                if supported_currencies:
                    if announcement_coin in supported_currencies:
                        logger.debug("Starting get_coin_info")
                        coin_info = get_coin_info(announcement_coin, pairing)

                        logger.debug('24h High: ' + coin_info.high_24h)
                        logger.debug('Coin price: ' + coin_info.last)
                        logger.debug('Finished get_coin_info')

                        try:
                            # Run a test trade if true
                            if config['TRADE_OPTIONS']['TEST']:
                                if float(coin_info.high_24h) > float(coin_info.last) + (float(coin_info.last) * float(ath) / 100):
                                    logger.info(f'24h High is {ath}% greater than price, coin not traded')
                                else:
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
                                    logger.debug(order[announcement_coin])
                            # place a live order if False
                            else:
                                if float(coin_info.high_24h) > float(coin_info.last) + (float(coin_info.last) * float(ath) / 100):
                                    logger.info(f'24h High is {ath}% greater than price, coin not traded')
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
                            if float(coin_info.high_24h) > float(coin_info.last) + (float(coin_info.last) * float(ath) / 100):
                                logger.info('No order status to report')
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


                                elif order_status == 'open' or order_status == 'cancelled':
                                    if not test_mode and order_status == 'open':
                                        # cancel orders and try again in the next iteration
                                        cancel_open_order(order[announcement_coin]['_id'], announcement_coin, pairing)
                                        logger.info(f"Cancelled order {order[announcement_coin]['_id']} .  Waiting for status of 'filled/closed' for {announcement_coin}")

                                    order.clear()  # reset for next iteration

                    else:
                        if announcement_coin:
                            logger.warning(f'{announcement_coin=} is not supported on gate io')
                            if os.path.isfile('new_listing.json'):
                                os.remove("new_listing.json")
                                logger.debug('Removed new_listing.json due to coin not being '
                                          'listed on gate io')
                else:
                    logger.error('supported_currencies is not initialized')
            else:

                logger.info( 'No coins announced, or coin has already been bought/sold.')


            time.sleep(3)
            # except Exception as e:
            # print(e)
    except KeyboardInterrupt:
        logger.info('Stopping Threads')
        globals.stop_threads = True
        t.join()
        t2.join()


if __name__ == '__main__':
    logger.info('working...')
    main()