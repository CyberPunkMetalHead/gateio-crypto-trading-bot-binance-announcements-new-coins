import itertools
import socket
import struct
import threading
import time
from typing import Callable

import requests

import gateio_new_coins_announcements_bot.globals as globals
from gateio_new_coins_announcements_bot.logger import logger


_proxy_list = {}
_proxy = None
_event = threading.Event()


def init_proxy():
    threading.Thread(target=lambda: _every(60 * 10, _fetch_proxies)).start()
    # Required for populating the proxy list when starting bot
    _fetch_proxies()


def _fetch_proxies():
    logger.info("Fetching proxies...")
    _proxy_list
    global _proxy
    threads: list[threading.Thread] = []
    try:
        proxy_res = requests.get(
            "https://www.proxyscan.io/api/proxy?last_check=180&limit=20&type=socks5&format=txt&ping=1000"
        ).text
    except requests.exceptions.RequestException as e:
        logger.error(f"Can't fetch proxies. Reason: {e}")
        return

    # Merging old proxies with new ones
    _merged_proxies = list(proxy_res[:-1].split("\n") | _proxy_list.keys())

    if len(_merged_proxies) > 0:
        for p in _merged_proxies:
            t = threading.Thread(target=checker, args=[p])
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    logger.info(f"Fetched {len(_proxy_list)} proxies")
    _proxy = itertools.cycle(_proxy_list.keys())


def get_proxy() -> str:
    try:
        return next(_proxy)
    except StopIteration as exc:
        raise Exception("No proxies available") from exc


def is_ready() -> bool:
    return len(_proxy_list) > 0


def set_proxy_event():
    _event.set()


# can be generalized and moved to separate file
def _every(delay: int, task: Callable):
    global _event
    next_time = time.time() + delay
    while not globals.stop_threads:
        _event.wait(max(0, next_time - time.time()))
        if not globals.stop_threads:
            try:
                task()
            except Exception as e:
                logger.error("Problem while fetching proxies")
                logger.debug(e)
        # skip tasks if we are behind schedule:
        next_time += (time.time() - next_time) // delay * delay + delay
    logger.info("Proxies fetching thread has stopped.")


def checker(proxy: str):
    global _proxy_list
    ip, port = proxy.split(":")
    sen = struct.pack("BBB", 0x05, 0x01, 0x00)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        try:
            s.connect((ip, int(port)))
            s.sendall(sen)

            data = s.recv(2)
            version, auth = struct.unpack("BB", data)
            # Check if the proxy is socks5 and it doesn't require authentication
            if version == 5 and auth == 0:
                _proxy_list[proxy] = proxy
            else:
                _proxy_list.pop(proxy, None)

        except Exception as e:
            logger.info(f"Proxy {proxy} invalid. Reason: {e}")
            _proxy_list.pop(proxy, None)
            return
