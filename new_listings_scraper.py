import ast
import os.path
import re
import time

import requests
from gate_api import ApiClient, SpotApi

from auth.gateio_auth import *
from logger import logger
from store_order import *

client = load_gateio_creds('auth/auth.yml')
spot_api = SpotApi(ApiClient(client))

global supported_currencies

def get_coins(pairing, page_num):
    """
    Scrapes new listings page for and returns new Symbols when appropriate
    """
    latest_announcement = requests.get(f"https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query?catalogId=48&pageNo={page_num}&pageSize=1&rnd={str(time.time())}")
    latest_announcement = latest_announcement.json()
    latest_announcement = latest_announcement['data']['articles'][0]['title']

    if "adds" in latest_announcement.lower() and "trading pairs" in latest_announcement.lower() and pairing in latest_announcement:
        found_pairs = re.findall(r'[A-Z]{1,10}[/][A-Z]*', latest_announcement)
        found_coins = [i.replace(f'/{pairing}', "") for i in found_pairs if i.find(pairing) != -1]
        return found_coins
    elif "will list" in latest_announcement.lower():
        found_coins = re.findall('\(([^)]+)', latest_announcement)
        if(len(found_coins) > 0):
            return found_coins
    
    return None


def get_last_coin(pairing):
    logger.debug("Pulling announcement page for [adds + trading pairs] or [will list] scenarios")

    found_coins = get_coins(pairing, 1)
    
    if len(found_coins) > 0:
        return found_coins
    
    return None


def store_new_listing(listing):
    """
    Only store a new listing if different from existing value
    """

    if os.path.isfile('new_listing.json'):
        file = load_order('new_listing.json')
        if set(listing) == set(file):
            return file
        else:
            store_order('new_listing.json', file)
            logger.info("New listing detected, updating file")
            return file
    else:
        new_listing = store_order('new_listing.json', listing)
        logger.info("File does not exist, creating file")

        return new_listing


def search_and_update(pairing):
    """
    Pretty much our main func
    """

    count = 57

    while True:
        time.sleep(3)
        try:
            latest_coins = get_last_coin(pairing)
            if len(latest_coins) > 0:
                store_new_listing(latest_coins)
            
            count = count + 3
            if count % 60 == 0:
                logger.info("One minute has passed.  Checking for coin announcements every 3 seconds (in a separate thread)")
                count = 0
        except Exception as e:
            logger.info(e)
    else:
        logger.info("while True loop in search_and_update has stopped.")


def get_all_currencies(single=False):
    """
    Get a list of all currencies supported on gate io
    :return:
    """
    global supported_currencies
    while True:
        logger.info("Getting the list of supported currencies from gate io")
        all_currencies = ast.literal_eval(str(spot_api.list_currencies()))
        currency_list = [currency['currency'] for currency in all_currencies]
        with open('currencies.json', 'w') as f:
            json.dump(currency_list, f, indent=4)
            logger.info("List of gate io currencies saved to currencies.json. Waiting 5 "
                  "minutes before refreshing list...")
        supported_currencies = currency_list
        if single:
            return supported_currencies
        else:
            time.sleep(300)
