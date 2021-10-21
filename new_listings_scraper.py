import ast

import requests
import os.path, json
import time

from store_order import *
from auth.gateio_auth import *
from gate_api import ApiClient, Configuration, Order, SpotApi
from load_config import *

client = load_gateio_creds('auth/auth.yml')
spot_api = SpotApi(ApiClient(client))

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
    enum = [item for item in enumerate(latest_announcement)]

    #Identify symbols in a string by using this janky, yet functional line
    uppers = ''.join(item[1] for item in enum if item[1].isupper() and (enum[enum.index(item)+1][1].isupper() or enum[enum.index(item)+1][1]==' ' or enum[enum.index(item)+1][1]==')') )
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

def get_all_currencies():
    """
    Get a list of all currencies supported on gate io
    :return:
    """
    while True:
        print("Getting the list of supported currencies from gate io")
        all_currencies = ast.literal_eval(str(spot_api.list_currencies()))
        currency_list = [currency['currency'] for currency in all_currencies]
        with open('currencies.json', 'w') as f:
            json.dump(currency_list, f, indent=4)
            print("List of gate io currencies saved to currencies.json. Waiting 5 "
                  "minutes before refreshing list...")
        time.sleep(300)