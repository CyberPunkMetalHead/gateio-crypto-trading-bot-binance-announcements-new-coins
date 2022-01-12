import random
import time
import requests

from gateio_new_coins_announcements_bot.logger import logger
from gateio_new_coins_announcements_bot.util.random import random_str, random_int


class BinanceScraper:
    def __init__(self, http_client=requests):
        self.http_client = http_client

    def fetch_latest_announcement(self):
        """
        Retrieves new coin listing announcements from binance.com
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
        return latest_announcement['data']['catalogs'][0]['articles'][0]['title']

    def __request_url(self):
        # Generate random query/params to help prevent caching
        queries = [
            "type=1",
            "catalogId=48",
            "pageNo=1",
            f"pageSize={str(random_int(maxInt=200))}",
            f"rnd={str(time.time())}",
            f"{random_str()}={str(random_int())}"
        ]
        random.shuffle(queries)
        return f"https://www.binance.com/gateway-api/v1/public/cms/article/list/query" \
               f"?{queries[0]}&{queries[1]}&{queries[2]}&{queries[3]}&{queries[4]}&{queries[5]}"
