import ast
import os.path
import random
import re
import string
import time
import re

import globals

import requests
from gate_api import ApiClient, SpotApi

from auth.gateio_auth import *
from logger import logger
from store_order import *

client = load_gateio_creds('auth/auth.yml')
spot_api = SpotApi(ApiClient(client))

global supported_currencies

previously_found_coins = set()


def get_announcement():
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
    return latest_announcement['data']['catalogs'][0]['articles'][0]['title']


def get_last_coin():
    """
     Returns new Symbol when appropriate
    """
    latest_announcement = get_announcement()

    found_coin = re.findall('\(([^)]+)', latest_announcement)

    # pull existing coin if file exists
    if os.path.isfile('new_listing.json'):
        existing_coin = load_order('new_listing.json')
    else:
        existing_coin = None

    uppers = None

    if 'Will List' not in latest_announcement or found_coin[0] == existing_coin or \
            found_coin[0] in previously_found_coins:
        return None
    else:
        if len(found_coin) == 1:
            uppers = found_coin[0]
            previously_found_coins.add(uppers)
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
    while not globals.stop_threads:
        sleep_time = 3
        for x in range(sleep_time):
            time.sleep(1)
            if globals.stop_threads:
                break
        try:
            latest_coin = get_last_coin()
            if latest_coin:
                store_new_listing(latest_coin)

            logger.info(f"Checking for coin announcements every {str(sleep_time)} seconds (in a separate thread)")
        except Exception as e:
            logger.info(e)
    else:
        logger.info("while True loop in search_and_update() has stopped.")


def get_all_currencies(single=False):
    """
    Get a list of all currencies supported on gate io
    :return:
    """
    global supported_currencies
    while not globals.stop_threads:
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
            for x in range(300):
                time.sleep(1)
                if globals.stop_threads:
                    break
    else:
        logger.info("while True loop in get_all_currencies() has stopped.")


def load_old_coins():
    with open('old_coins.json') as json_file:
        data = json.load(json_file)
        logger.debug("Loaded old_coins from file")
        return data


def store_old_coins(old_coin_list):
    with open('old_coins.json', 'w') as f:
        json.dump(old_coin_list, f, indent=2)
        logger.debug('Wrote old_coins to file')
