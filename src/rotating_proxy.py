# import random
from typing import Callable
import requests
import threading
import time
import itertools

import urllib.request
import gateio_new_coins_announcements_bot.globals as globals
from gateio_new_coins_announcements_bot.logger import logger


_proxy_list = {}
_proxy = None
event = threading.Event()


def init_proxy():
    threading.Thread(target=lambda: _every(60 * 10, _fetch_proxies)).start()


def _fetch_proxies():
    logger.info("Fetching proxies...")
    global _proxy_list
    global _proxy
    _proxy_list = {}
    # threads = []
    try:
        proxy_res = requests.get(
            "https://www.proxyscan.io/api/proxy?last_check=180&limit=20&type=socks5&format=txt&ping=1000"
        ).text
    except requests.exceptions.RequestException as e:
        logger.error(e)
    print(proxy_res)

    for p in proxy_res.split("\n"):
        _proxy_list[p] = p

    """
    list = proxy_res.split("\n")

    if len(list) > 0:
        for p in list:
            t = threading.Thread(target=checker, args=[p])
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
    """
    logger.info(f"Fetched {len(_proxy_list)} proxies")
    _proxy = itertools.cycle(_proxy_list.keys())


def get_proxy() -> str:
    return next(_proxy)


def is_ready() -> bool:
    return len(_proxy_list) > 0


# can be generalized and moved to separate file
def _every(delay: int, task: Callable):
    global event
    next_time = time.time() + delay
    while not globals.stop_threads:
        event.wait(max(0, next_time - time.time()))
        try:
            task()
        except Exception:
            logger.error("Problem while fetching proxies")
        # skip tasks if we are behind schedule:
        next_time += (time.time() - next_time) // delay * delay + delay
    logger.info("Proxies fetching thread has stopped.")


def checker(proxy):
    global _proxy_list
    user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) \
        Ubuntu Chromium/37.0.2062.94 Chrome/37.0.2062.94 Safari/537.36"
    site = "https://binance.com/"
    proxy_support = urllib.request.ProxyHandler({"https": proxy})
    opener = urllib.request.build_opener(proxy_support)
    urllib.request.install_opener(opener)
    req = urllib.request.Request("https://" + site)
    req.add_header("User-Agent", user_agent)
    try:
        start_time = time.time()
        urllib.request.urlopen(req, timeout=1000)
        end_time = time()
        time_taken = end_time - start_time
        print("%s works!" % proxy)
        print("time: " + str(time_taken))
        print("user_agent: " + user_agent + "\n")
        _proxy_list[proxy] = proxy
        return
    except Exception as e:
        print(e)
        pass
        print("%s does not respond.\n" % proxy)
        return


# Required for populating the proxy list when starting bot
_fetch_proxies()
