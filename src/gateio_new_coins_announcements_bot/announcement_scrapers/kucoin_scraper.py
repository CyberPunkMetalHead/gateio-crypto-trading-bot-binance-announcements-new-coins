import random
import time
import requests

from gateio_new_coins_announcements_bot.logger import logger
from gateio_new_coins_announcements_bot.util.random import random_str, random_int


class KucoinScraper:
    def __init__(self, http_client=requests):
        self.http_client = http_client

    def fetch_latest_announcement(self):
        """
        Retrieves new coin listing announcements from kucoin.com
        """
        logger.debug("Pulling announcement page")
        request_url = self.__request_url()
        response = self.http_client.get(request_url)

        # Raise an HTTPError if status is not 200
        response.raise_for_status()

        if "X-Cache" in response.headers:
            logger.debug(f'Response was cached. Contains headers X-Cache: {response.headers["X-Cache"]}')
        else:
            logger.debug(f'Hit the source directly (no cache)')

        latest_announcement = response.json()
        logger.debug("Finished pulling announcement page")
        return latest_announcement['items'][0]['title']

    def __request_url(self):
        # Generate random query/params to help prevent caching
        queries = [
            "page=1",
            f"pageSize={str(random_int(maxInt=200))}",
            "category=listing",
            "lang=en_US",
            f"rnd={str(time.time())}",
            f"{random_str()}={str(random_int())}"
        ]
        random.shuffle(queries)

        return f"https://www.kucoin.com/_api/cms/articles?" \
               f"?{queries[0]}&{queries[1]}&{queries[2]}&{queries[3]}&{queries[4]}&{queries[5]}"
