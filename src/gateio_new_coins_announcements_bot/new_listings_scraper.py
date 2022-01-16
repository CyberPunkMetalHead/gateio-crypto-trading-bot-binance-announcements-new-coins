import ast
import json
import os.path
import random
import re
import string
import time

import requests
from gate_api import ApiClient
from gate_api import SpotApi

import gateio_new_coins_announcements_bot.globals as globals
from gateio_new_coins_announcements_bot.auth.gateio_auth import load_gateio_creds
from gateio_new_coins_announcements_bot.load_config import load_config
from gateio_new_coins_announcements_bot.logger import logger
from gateio_new_coins_announcements_bot.store_order import load_order

config = load_config("config.yml")
client = load_gateio_creds("auth/auth.yml")
spot_api = SpotApi(ApiClient(client))

supported_currencies = None

previously_found_coins = set()


def get_announcement():
    """
    Retrieves new coin listing announcements

    """
    logger.debug("Pulling announcement page")
    # Generate random query/params to help prevent caching
    rand_page_size = random.randint(1, 200)
    letters = string.ascii_letters
    random_string = "".join(random.choice(letters) for i in range(random.randint(10, 20)))
    random_number = random.randint(1, 99999999999999999999)
    queries = [
        "type=1",
        "catalogId=48",
        "pageNo=1",
        f"pageSize={str(rand_page_size)}",
        f"rnd={str(time.time())}",
        f"{random_string}={str(random_number)}",
    ]
    random.shuffle(queries)
    logger.debug(f"Queries: {queries}")
    request_url = (
        f"https://www.binance.com/gateway-api/v1/public/cms/article/list/query"
        f"?{queries[0]}&{queries[1]}&{queries[2]}&{queries[3]}&{queries[4]}&{queries[5]}"
    )

    latest_announcement = requests.get(request_url)
    if latest_announcement.status_code == 200:
        try:
            logger.debug(f'X-Cache: {latest_announcement.headers["X-Cache"]}')
        except KeyError:
            # No X-Cache header was found - great news, we're hitting the source.
            pass

        latest_announcement = latest_announcement.json()
        logger.debug("Finished pulling announcement page")
        return latest_announcement["data"]["catalogs"][0]["articles"][0]["title"]
    else:
        logger.error(f"Error pulling binance announcement page: {latest_announcement.status_code}")
        return ""


def get_kucoin_announcement():
    """
    Retrieves new coin listing announcements from Kucoin

    """
    logger.debug("Pulling announcement page")
    # Generate random query/params to help prevent caching
    rand_page_size = random.randint(1, 200)
    letters = string.ascii_letters
    random_string = "".join(random.choice(letters) for i in range(random.randint(10, 20)))
    random_number = random.randint(1, 99999999999999999999)
    queries = [
        "page=1",
        f"pageSize={str(rand_page_size)}",
        "category=listing",
        "lang=en_US",
        f"rnd={str(time.time())}",
        f"{random_string}={str(random_number)}",
    ]
    random.shuffle(queries)
    logger.debug(f"Queries: {queries}")
    request_url = (
        f"https://www.kucoin.com/_api/cms/articles?"
        f"?{queries[0]}&{queries[1]}&{queries[2]}&{queries[3]}&{queries[4]}&{queries[5]}"
    )
    latest_announcement = requests.get(request_url)
    if latest_announcement.status_code == 200:
        try:
            logger.debug(f'X-Cache: {latest_announcement.headers["X-Cache"]}')
        except KeyError:
            # No X-Cache header was found - great news, we're hitting the source.
            pass

        latest_announcement = latest_announcement.json()
        logger.debug("Finished pulling announcement page")
        return latest_announcement["items"][0]["title"]
    else:
        logger.error(f"Error pulling kucoin announcement page: {latest_announcement.status_code}")
        return ""

def _extract_coins_from_announcement(annoucement):
    word_blacklist = [
        "Innovation Zone",
        "Binance Futures",
        "Launchpool"
    ]

    for word in word_blacklist:
        if word in annoucement:
            logger.info(f"Latest announcement: {annoucement}")
            logger.info(f"Blacklisted word: \"{word}\" found in announcement, skipping")
            return None

    return re.findall(r"\(([^)]+)\)", annoucement)


def get_last_coin():
    """
    Returns new Symbol when appropriate
    """
    # scan Binance Announcement
    logger.info("Scanning Binance Announcement page...")
    latest_announcement = get_announcement()

    coins = _extract_coins_from_announcement(latest_announcement)

    # if Kucoin Announcements are enabled in config
    if config["TRADE_OPTIONS"]["KUCOIN_ANNOUNCEMENTS"]:
        logger.info("Kucoin announcements enabled, look for new Kucoin coins...")
        kucoin_announcement = get_kucoin_announcement()
        kucoin_coin = _extract_coins_from_announcement(kucoin_announcement)
        coins.extend(kucoin_coin)

    if len(coins) > 0:
        logger.debug(f"Detected {len(coins)} coins from announcements: {coins}. Picking first new coin...")
        for coin in coins:
            # return coin first new coin
            if coin != globals.latest_listing and coin not in previously_found_coins:
                    previously_found_coins.add(coin)
                    logger.info("New coin detected: " + coin)
                    return coin

    logger.debug("No new coins found")
    return None

def store_new_listing(listing):
    """
    Only store a new listing if different from existing value
    """
    if listing and not listing == globals.latest_listing:
        logger.info("New listing detected")
        globals.latest_listing = listing
        globals.buy_ready.set()


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
            elif globals.test_mode and os.path.isfile("test_new_listing.json"):
                store_new_listing(load_order("test_new_listing.json"))
                if os.path.isfile("test_new_listing.json.used"):
                    os.remove("test_new_listing.json.used")
                os.rename("test_new_listing.json", "test_new_listing.json.used")
            logger.info(f"Checking for coin announcements every {str(sleep_time)} seconds (in a separate thread)")
        except Exception as e:
            logger.info(e)
    else:
        logger.info("while loop in search_and_update() has stopped.")


def get_all_currencies(single=False):
    """
    Get a list of all currencies supported on gate io
    :return:
    """
    global supported_currencies
    while not globals.stop_threads:
        logger.info("Getting the list of supported currencies from gate io")
        all_currencies = ast.literal_eval(str(spot_api.list_currencies()))
        currency_list = [currency["currency"] for currency in all_currencies]
        with open("currencies.json", "w") as f:
            json.dump(currency_list, f, indent=4)
            logger.info(
                "List of gate io currencies saved to currencies.json. Waiting 5 " "minutes before refreshing list..."
            )
        supported_currencies = currency_list
        if single:
            return supported_currencies
        else:
            for x in range(300):
                time.sleep(1)
                if globals.stop_threads:
                    break
    else:
        logger.info("while loop in get_all_currencies() has stopped.")


def load_old_coins():
    if os.path.isfile("old_coins.json"):
        with open("old_coins.json") as json_file:
            data = json.load(json_file)
            logger.debug("Loaded old_coins from file")
            return data
    else:
        return []


def store_old_coins(old_coin_list):
    with open("old_coins.json", "w") as f:
        json.dump(old_coin_list, f, indent=2)
        logger.debug("Wrote old_coins to file")
