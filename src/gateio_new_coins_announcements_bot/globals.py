import threading

buy_ready = threading.Event()
sell_ready = threading.Event()
stop_threads = False
old_coins = {}
latest_listing = ""

#TRADE_OPTIONS config values
quantity = 15
pairing = "USDT"
test_mode = True
sl = -3
tp = 2
enable_tsl = True
tsl = -4
ttp = 2
