import ast
import json
import os.path
import re
import time

from gate_api import ApiClient
from gate_api import SpotApi

import gateio_new_coins_announcements_bot.globals as globals
from gateio_new_coins_announcements_bot.announcement_scrapers.binance_scraper import BinanceScraper
from gateio_new_coins_announcements_bot.announcement_scrapers.kucoin_scraper import KucoinScraper
from gateio_new_coins_announcements_bot.auth.gateio_auth import load_gateio_creds
from gateio_new_coins_announcements_bot.load_config import load_config
from gateio_new_coins_announcements_bot.logger import logger
from gateio_new_coins_announcements_bot.store_order import load_order
import rotating_proxy

config = load_config("config.yml")
client = load_gateio_creds("auth/auth.yml")
spot_api = SpotApi(ApiClient(client))

supported_currencies = None

previously_found_coins = set()


def get_last_coin():
    """
    Returns new Symbol when appropriate
    """
    # scan Binance Announcement
    latest_announcement = BinanceScraper().fetch_latest_announcement()

    # enable Kucoin Announcements if True in config
    if config["TRADE_OPTIONS"]["KUCOIN_ANNOUNCEMENTS"]:
        logger.info("Kucoin announcements enabled, look for new Kucoin coins...")
        kucoin_announcement = KucoinScraper().fetch_latest_announcement()
        kucoin_coin = re.findall(r"\(([^)]+)", kucoin_announcement)

    found_coin = re.findall(r"\(([^)]+)", latest_announcement)
    uppers = None

    # returns nothing if it's an old coin or it's not an actual coin listing
    if (
        "Will List" not in latest_announcement
        or found_coin[0] == globals.latest_listing
        or found_coin[0] in previously_found_coins
    ):

        # if the latest Binance announcement is not a new coin listing,
        # or the listing has already been returned, check kucoin
        if (
            config["TRADE_OPTIONS"]["KUCOIN_ANNOUNCEMENTS"]
            and "Gets Listed" in kucoin_announcement
            and kucoin_coin[0] != globals.latest_listing
            and kucoin_coin[0] not in previously_found_coins
        ):
            if len(kucoin_coin) == 1:
                uppers = kucoin_coin[0]
                previously_found_coins.add(uppers)
                logger.info("New Kucoin coin detected: " + uppers)
            if len(kucoin_coin) != 1:
                uppers = None

    else:
        if len(found_coin) == 1:
            uppers = found_coin[0]
            previously_found_coins.add(uppers)
            logger.info("New coin detected: " + uppers)
        if len(found_coin) != 1:
            uppers = None

    return uppers


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
