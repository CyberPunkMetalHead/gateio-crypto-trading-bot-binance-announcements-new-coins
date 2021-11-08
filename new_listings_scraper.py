import ast
import os.path
import re
import time
import random
import string

import requests
from gate_api import ApiClient, SpotApi

from auth.gateio_auth import *
from logger import logger
from store_order import *
from trade_client import *
import globals

client = load_gateio_creds('auth/auth.yml')
spot_api = SpotApi(ApiClient(client))

global supported_currencies



def get_announcement(pairing):
    """
    Retrieves new coin listing announcements
    """
    logger.debug("Pulling announcement page")
    # Generate random query/params to help prevent caching
    rand_page_size = random.randint(1, 200)
    letters = string.ascii_letters
    random_string = ''.join(random.choice(letters) for i in range(random.randint(10, 20)))
    random_number = random.randint(1, 99999999999999999999)
    queries = ["type=1", "catalogId=48", "pageNo=1", f"pageSize={str(rand_page_size)}", f"rnd={str(time.time())}",
               f"{random_string}={str(random_number)}"]
    random.shuffle(queries)
    logger.debug(f"Queries: {queries}")
    request_url = f"https://www.binancezh.com/gateway-api/v1/public/cms/article/list/query" \
                  f"?{queries[0]}&{queries[1]}&{queries[2]}&{queries[3]}&{queries[4]}&{queries[5]}"
    latest_announcement = requests.get(request_url)
    try:
        logger.debug(f'X-Cache: {latest_announcement.headers["X-Cache"]}')
    except KeyError:
        # No X-Cache header was found - great news, we're hitting the source.
        pass

    latest_announcement = latest_announcement.json()
    logger.debug("Finished pulling announcement page")

    announcement = latest_announcement['data']['catalogs'][0]['articles'][0]['title']

    return get_coins_by_accouncement_text(announcement, pairing)



def get_coins_by_accouncement_text(latest_announcement, pairing):
    
    if "adds" in latest_announcement.lower() and "trading pair" in latest_announcement.lower() and pairing in latest_announcement:
        found_pairs = re.findall(r'[A-Z]{1,10}[/][A-Z]*', latest_announcement)
        found_coins = [i.replace(f'/{pairing}', "") for i in found_pairs if i.find(pairing) != -1]
        return found_coins
    elif "will list" in latest_announcement.lower():
        found_coins = re.findall('\(([^)]+)', latest_announcement)
        if(len(found_coins) > 0):
            return found_coins
    
    return False



def get_newly_listed_coin(pairing, new_listings):
    logger.debug("Pulling announcement page for [adds + trading pairs] or [will list] scenarios")

    if len(new_listings) == 0:
        return False
    else:
        symbol = new_listings[0]
    
    found_coins = get_coins_by_accouncement_text(f"Will list ({symbol})", pairing)    
    
    if found_coins and len(found_coins) > 0:
        return found_coins
    
    return False


def read_newly_listed(file):
    """
    Get user inputed new listings (see https://www.gate.io/en/marketlist?tab=newlisted)
    """
    with open(file, "r+") as f:
        return json.load(f)

def store_newly_listed(listings):
    """
    Save order into local json file
    """
    with open('newly_listed.json', 'w') as f:
        json.dump(listings, f, indent=4)


def store_new_listing(listing):
    """
    Only store a new listing if different from existing value
    """

    if os.path.isfile('new_listing.json'):
        file = load_order('new_listing.json')
        if set(listing).intersection(set(file)) == set(listing):
            return False
        else:
            joined = file + listing
           
            with open('new_listing.json', 'w') as f:
                json.dump(joined, f, indent=4)
            
            logger.info("New listing detected, updating file")
            return file
    else:
        new_listing = store_order('new_listing.json', listing)
        logger.info("File does not exist, creating file")

        return new_listing


def search_binance_and_update(pairing):
    """
    Pretty much our main func for binance
    """
    count = 57
    while not globals.stop_threads:
        sleep_time = 3
        for x in range(sleep_time):
            time.sleep(1)
            if globals.stop_threads:
                break
        try:
            latest_coins = get_announcement(pairing)
            if latest_coins and len(latest_coins) > 0:
                store_new_listing(latest_coins)
            
            count = count + 3
            if count % 60 == 0:
                logger.info("One minute has passed.  Checking for coin announcements on Binanace every 3 seconds (in a separate thread)")
                count = 0
        except Exception as e:
            logger.info(e)

        



def search_gateio_and_update(pairing, new_listings):
    """
    Pretty much our main func for gateio listings
    """
    count = 59
    while not globals.stop_threads:
        
        latest_coins = get_newly_listed_coin(pairing, new_listings)
        if latest_coins:
            try:
                #ready = is_currency_trade_ready(latest_coins[0], pairing)
                price = get_last_price(latest_coins[0], pairing, True)
                if float(price) > 0:
                        logger.info(f"Found new 'tradable' coin {latest_coins[0]} with a price of {price}!! Adding to new listings.")
                    
                        # store as announcement coin for main thread to pick up (It's go time!!!)
                        store_new_listing(latest_coins)

                        # remove from list of coins to be listed
                        new_listings.pop(0)
                
                
            except GateApiException as e:
                if e.label != "INVALID_CURRENCY":
                    logger.error(e)
            except Exception as e:
                logger.info(e)
        
        
        
        count = count + 1
        if count % 60 == 0:
            logger.info("One minute has passed.  Checking for coin listing on Gate.io every 3 seconds (in a separate thread)")
            count = 0
       
        time.sleep(1)
        if globals.stop_threads:
                break


def get_all_currencies(single=False):
    """
    Get a list of all currencies supported on gate io
    :return:
    """
    global supported_currencies
    while not globals.stop_threads:
        logger.info("Getting the list of supported currencies from gate io")
        response = spot_api.list_currencies()
        all_currencies = ast.literal_eval(str(response))
        currency_list = [currency['currency'] for currency in all_currencies]
        with open('currencies.json', 'w') as f:
            json.dump(currency_list, f, indent=4)
            logger.info("List of gate io currencies saved to currencies.json. Waiting 5 "
                  "minutes before refreshing list...")
        supported_currencies = currency_list
        if single:
            return supported_currencies
        else:
            for x in range(300):
                time.sleep(1)
                if globals.stop_threads:
                    break

      


