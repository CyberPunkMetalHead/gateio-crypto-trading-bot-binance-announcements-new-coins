import ast
import os.path
import random
import re
import string
import time
import re

import requests
from gate_api import ApiClient, SpotApi

from auth.gateio_auth import *
from logger import logger
from store_order import *

client = load_gateio_creds('auth/auth.yml')
spot_api = SpotApi(ApiClient(client))

global supported_currencies


def get_last_coin():
    """
    Scrapes new listings page for and returns new Symbol when appropriate
    """
    logger.debug("Pulling announcement page")
    # Generate random query/params to help prevent caching
    rand_page_size = random.randint(1, 200)
    letters = string.ascii_letters
    random_string = ''.join(random.choice(letters) for i in range(random.randint(10, 20)))
    random_number = random.randint(1, 99999999999999999999)
    queries = ["catalogId=48", "pageNo=1", f"pageSize={str(rand_page_size)}", f"rnd={str(time.time())}", f"{random_string}={str(random_number)}"]
    random.shuffle(queries)
    logger.debug(f"Queries: {queries}")
    request_url = f"https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query?{queries[0]}&{queries[1]}&{queries[2]}&{queries[3]}&{queries[4]}"
    latest_announcement = requests.get(request_url)
    logger.debug(f'X-Cache: {latest_announcement.headers["X-Cache"]}')
    latest_announcement = latest_announcement.json()
    logger.debug("Finished pulling announcement page")
    latest_announcement = latest_announcement['data']['articles'][0]['title']
    found_coin = re.findall('\(([^)]+)', latest_announcement)

    # pull existing coin if file exists
    if os.path.isfile('new_listing.json'):
        existing_coin = load_order('new_listing.json')
    else:
        existing_coin = None
        
    uppers = None

    if 'Will List' not in latest_announcement or found_coin[0] == existing_coin:
        return None
    else:
        if len(found_coin) == 1:
            uppers = found_coin[0]
            logger.info('New coin detected: ' + uppers)
        if len(found_coin) != 1:
            uppers = None
    print(f'{uppers=}')
    return uppers


def store_new_listing(listing):
    """
    Only store a new listing if different from existing value
    """

    if os.path.isfile('new_listing.json'):
        file = load_order('new_listing.json')
        if listing in file:
            return file
        else:
            file = listing
            store_order('new_listing.json', file)
            logger.info("New listing detected, updating file")
            return file
    else:
        new_listing = store_order('new_listing.json', listing)
        logger.info("File does not exist, creating file")

        return new_listing


def search_and_update():
    """
    Pretty much our main func
    """
    while True:
        time.sleep(3)
        try:
            latest_coin = get_last_coin()
            if latest_coin:
                store_new_listing(latest_coin)
            logger.info("Checking for coin announcements every 1 minute (in a separate "
                       "thread)")
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
