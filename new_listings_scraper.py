import requests
import os.path, json
import time
import re

from store_order import *
from load_config import *


def get_last_coin():
    """
    Scrapes new listings page for and returns new Symbol when appropriate
    """
    latest_announcement = requests.get("https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query?catalogId=48&pageNo=1&pageSize=15")
    latest_announcement = latest_announcement.json()
    latest_announcement = latest_announcement['data']['articles'][0]['title']

    # Binance makes several annoucements, irrevelant ones will be ignored
    exclusions = ['Futures', 'Margin', 'adds', 'Adds']
    for item in exclusions:
        if item in latest_announcement:
            return None
    uppers = re.match(r".*\s([A-Z]{2,}).*", latest_announcement).group(1)
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
            print("New listing detected, updating file")
            return file
    else:
        new_listing = store_order('new_listing.json', listing)
        print("File does not exist, creating file")

        return new_listing


def search_and_update():
    """
    Pretty much our main func
    """
    while True:
        latest_coin = get_last_coin()
        if latest_coin:
            store_new_listing(latest_coin)
        print("Checking for coin announcements every 1 minute (in a separate thread)")

        time.sleep(10)
