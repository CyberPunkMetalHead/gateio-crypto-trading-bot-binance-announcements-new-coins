from trade_client import *
from store_order import *
from load_config import *
from new_listings_scraper import *

from collections import defaultdict
from datetime import datetime, time
import time
import threading

import json
import os.path


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
supported_currencies = get_all_currencies(single=True)


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
    frequency = config['TRADE_OPTIONS']['RUN_EVERY']
    test_mode = config['TRADE_OPTIONS']['TEST']

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
                stored_price = float(order[coin]['price'])
                coin_tp = order[coin]['tp']
                coin_sl = order[coin]['sl']
                volume = order[coin]['volume']
                symbol = order[coin]['symbol']

                last_price = get_last_price(symbol, pairing)
                print(f'{last_price=}')
                print(f'{stored_price - (stored_price*sl /100)=}')
                # update stop loss and take profit values if threshold is reached
                if float(last_price) > stored_price + (stored_price*coin_tp /100) and enable_tsl:
                    # increase as absolute value for TP
                    new_tp = float(last_price) - (float(last_price)*ttp /100)
                    # convert back into % difference from when the coin was bought
                    new_tp = float( (new_tp - stored_price) / stored_price*100)

                    # same deal as above, only applied to trailing SL
                    new_sl = float(last_price) + (float(last_price)*tsl /100)
                    new_sl = float((new_sl - stored_price) / stored_price*100)

                    # new values to be added to the json file
                    order[coin]['tp'] = new_tp
                    order[coin]['sl'] = new_sl
                    store_order('order.json', order)

                    print(f'updated tp: {round(new_tp, 3)} and sl: {round(new_sl, 3)}')

                # close trade if tsl is reached or trail option is not enabled
                elif float(last_price) < stored_price - (stored_price*sl /100) or float(last_price) > stored_price + (stored_price*coin_tp /100) and not enable_tsl:
                    try:
                        # sell for real if test mode is set to false
                        if not test_mode:
                            sell = place_order(symbol, pairing, coin['volume']*99.5/100, 'sell', last_price)

                        print(f"sold {coin} with {(float(last_price) - stored_price) / float(stored_price)*100}% PNL")

                        # remove order from json file
                        order.pop(coin)
                        store_order('order.json', order)

                    except Exception as e:
                        print(e)

                    # store sold trades data
                    else:
                        if not test_mode:
                            sold_coins[coin] = sell
                            store_order('sold.json', sold_coins)
                        else:
                            sold_coins[coin] = {
                                        'symbol':coin,
                                        'price':last_price,
                                        'volume':volume,
                                        'time':datetime.timestamp(datetime.now()),
                                        'profit': float(last_price) - stored_price,
                                        'relative_profit_%': round((float(last_price) - stored_price) / stored_price*100, 3),
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
                                        'price': last_price }

                            store_order('sold.json', sold_coins)


        # the buy block and logic pass
        #announcement_coin = load_order('new_listing.json')
        if os.path.isfile('new_listing.json'):
            announcement_coin = load_order('new_listing.json')
        else:
            announcement_coin = False

        global supported_currencies
        if announcement_coin and announcement_coin not in order and announcement_coin not in sold_coins:
            print(f'New annoucement detected: {announcement_coin}')
            # if os.path.isfile('currencies.json'):
                # supported_currencies = json.load(open('currencies.json',))
            if supported_currencies is not False:
                if announcement_coin in supported_currencies:
                    price = get_last_price(announcement_coin, pairing)
                    try:
                        # Run a test trade if true
                        if config['TRADE_OPTIONS']['TEST']:
                            order[announcement_coin] = {
                                        'symbol':announcement_coin,
                                        'price':price,
                                        'volume':qty,
                                        'time':datetime.timestamp(datetime.now()),
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
                            print('PLACING TEST ORDER')
                        # place a live order if False
                        else:
                            order[announcement_coin] = place_order(announcement_coin, pairing, qty,'buy', price)
                            order[announcement_coin]['tp'] = tp
                            order[announcement_coin]['sl'] = sl

                    except Exception as e:
                        print(e)

                    else:
                        print(f"Order created with {qty} on {announcement_coin}")

                        store_order('order.json', order)
                else:
                    print(f"Coin " + announcement_coin + " is not supported on gate io")
                    os.remove("new_listing.json")
            else:
                get_all_currencies()
        else:
            print(f"No coins announced, or coin has already been bought/sold. Checking more frequently in case TP and SL need updating. You can comment me out, I live on line 176 in main.py")

        time.sleep(3)
        #except Exception as e:
            #print(e)



if __name__ == '__main__':
    print('working...')
    main()
