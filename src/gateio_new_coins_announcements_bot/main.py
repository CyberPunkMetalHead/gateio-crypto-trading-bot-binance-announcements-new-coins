import copy
import os.path
import threading
import time
from datetime import datetime

import gateio_new_coins_announcements_bot.globals as globals
from gateio_new_coins_announcements_bot.load_config import load_config
from gateio_new_coins_announcements_bot.logger import logger
from gateio_new_coins_announcements_bot.new_listings_scraper import get_all_currencies
from gateio_new_coins_announcements_bot.new_listings_scraper import get_last_coin
from gateio_new_coins_announcements_bot.new_listings_scraper import load_old_coins
from gateio_new_coins_announcements_bot.new_listings_scraper import search_and_update
from gateio_new_coins_announcements_bot.new_listings_scraper import store_old_coins
from gateio_new_coins_announcements_bot.store_order import load_order
from gateio_new_coins_announcements_bot.store_order import store_order
from gateio_new_coins_announcements_bot.trade_client import get_last_price
from gateio_new_coins_announcements_bot.trade_client import place_order

_sold_coins = {}
_order = {}
_session = {}
_supported_currencies = None


def buy():
    while not globals.stop_threads:
        logger.debug("Waiting for buy_ready event")
        globals.buy_ready.wait()
        logger.debug("buy_ready event triggered")
        if globals.stop_threads:
            break
        announcement_coin = globals.latest_listing

        global _supported_currencies
        if (
            announcement_coin
            and announcement_coin not in _order
            and announcement_coin not in _sold_coins
            and announcement_coin not in globals.old_coins
        ):

            logger.info(f"New announcement detected: {announcement_coin}", extra={"TELEGRAM": "COIN_ANNOUNCEMENT"})

            if not _supported_currencies:
                _supported_currencies = get_all_currencies(single=True)
            if _supported_currencies:
                if announcement_coin in _supported_currencies:
                    logger.debug("Starting get_last_price")

                    # get latest price object
                    obj = get_last_price(announcement_coin, globals.pairing, False)
                    price = obj.price

                    if float(price) <= 0:
                        continue  # wait for positive price

                    if announcement_coin not in _session:
                        _session[announcement_coin] = {}
                        _session[announcement_coin].update({"total_volume": 0})
                        _session[announcement_coin].update({"total_amount": 0})
                        _session[announcement_coin].update({"total_fees": 0})
                        _session[announcement_coin]["orders"] = list()

                    # initalize order object
                    if announcement_coin not in _order:
                        volume = globals.quantity - _session[announcement_coin]["total_volume"]

                        _order[announcement_coin] = {}
                        _order[announcement_coin]["_amount"] = f"{volume / float(price)}"
                        _order[announcement_coin]["_left"] = f"{volume / float(price)}"
                        _order[announcement_coin]["_fee"] = f"{0}"
                        _order[announcement_coin]["_tp"] = f"{0}"
                        _order[announcement_coin]["_sl"] = f"{0}"
                        _order[announcement_coin]["_status"] = "unknown"
                        if announcement_coin in _session:
                            if len(_session[announcement_coin]["orders"]) == 0:
                                _order[announcement_coin]["_status"] = "test_partial_fill_order"
                            else:
                                _order[announcement_coin]["_status"] = "cancelled"

                    amount = float(_order[announcement_coin]["_amount"])
                    left = float(_order[announcement_coin]["_left"])
                    status = _order[announcement_coin]["_status"]

                    if left - amount != 0:
                        # partial fill.
                        amount = left

                    logger.info(
                        f"starting buy place_order with : {announcement_coin=} | {globals.pairing=} | {volume=} | "
                        + f"{amount=} x {price=} | side = buy | {status=}",
                        extra={"TELEGRAM": "BUY_START"},
                    )

                    try:
                        # Run a test trade if true
                        if globals.test_mode:
                            if _order[announcement_coin]["_status"] == "cancelled":
                                status = "closed"
                                left = 0
                                fee = f"{float(amount) * .002}"
                            else:
                                status = "cancelled"
                                left = f"{amount *.66}"
                                fee = f"{float(amount - float(left)) * .002}"

                            _order[announcement_coin] = {
                                "_fee_currency": announcement_coin,
                                "_price": f"{price}",
                                "_amount": f"{amount}",
                                "_time": datetime.timestamp(datetime.now()),
                                "_tp": globals.tp,
                                "_sl": globals.sl,
                                "_ttp": globals.ttp,
                                "_tsl": globals.tsl,
                                "_id": "test-order",
                                "_text": "test-order",
                                "_create_time": datetime.timestamp(datetime.now()),
                                "_update_time": datetime.timestamp(datetime.now()),
                                "_currency_pair": f"{announcement_coin}_{globals.pairing}",
                                "_status": status,
                                "_type": "limit",
                                "_account": "spot",
                                "_side": "buy",
                                "_iceberg": "0",
                                "_left": f"{left}",
                                "_fee": fee,
                            }
                            logger.info("PLACING TEST ORDER")
                            logger.info(_order[announcement_coin])
                        # place a live order if False
                        else:
                            # just in case...stop buying more than our config amount
                            assert amount * float(price) <= float(volume)

                            _order[announcement_coin] = place_order(
                                announcement_coin, globals.pairing, volume, "buy", price
                            )
                            _order[announcement_coin] = _order[announcement_coin].__dict__
                            _order[announcement_coin].pop("local_vars_configuration")
                            _order[announcement_coin]["_tp"] = globals.tp
                            _order[announcement_coin]["_sl"] = globals.sl
                            _order[announcement_coin]["_ttp"] = globals.ttp
                            _order[announcement_coin]["_tsl"] = globals.tsl
                            logger.debug("Finished buy place_order")

                    except Exception as e:
                        logger.error(e)

                    else:
                        order_status = _order[announcement_coin]["_status"]

                        logger.info(
                            f"Order created on {announcement_coin=} at a price of {price} each.  {order_status=}",
                            extra={"TELEGRAM": "BUY_ORDER_CREATED"},
                        )

                        if order_status == "closed":
                            _order[announcement_coin]["_amount_filled"] = _order[announcement_coin]["_amount"]
                            _session[announcement_coin]["total_volume"] += float(
                                _order[announcement_coin]["_amount"]
                            ) * float(_order[announcement_coin]["_price"])
                            _session[announcement_coin]["total_amount"] += float(_order[announcement_coin]["_amount"])
                            _session[announcement_coin]["total_fees"] += float(_order[announcement_coin]["_fee"])
                            _session[announcement_coin]["orders"].append(copy.deepcopy(_order[announcement_coin]))

                            # update order to sum all amounts and all fees
                            # this will set up our sell order for sale of all filled buy orders
                            tf = _session[announcement_coin]["total_fees"]
                            ta = _session[announcement_coin]["total_amount"]
                            _order[announcement_coin]["_fee"] = f"{tf}"
                            _order[announcement_coin]["_amount"] = f"{ta}"

                            store_order("order.json", _order)
                            store_order("session.json", _session)

                            # We're done. Stop buying and finish up the selling.
                            globals.sell_ready.set()
                            globals.buy_ready.clear()

                            logger.info(f"Order on {announcement_coin} closed", extra={"TELEGRAM": "BUY_FILLED"})
                        else:
                            if (
                                order_status == "cancelled"
                                and float(_order[announcement_coin]["_amount"])
                                > float(_order[announcement_coin]["_left"])
                                and float(_order[announcement_coin]["_left"]) > 0
                            ):
                                # partial order. Change qty and fee_total in order and finish any remaining balance
                                partial_amount = float(_order[announcement_coin]["_amount"]) - float(
                                    _order[announcement_coin]["_left"]
                                )
                                partial_fee = float(_order[announcement_coin]["_fee"])
                                _order[announcement_coin]["_amount_filled"] = f"{partial_amount}"
                                _session[announcement_coin]["total_volume"] += partial_amount * float(
                                    _order[announcement_coin]["_price"]
                                )
                                _session[announcement_coin]["total_amount"] += partial_amount
                                _session[announcement_coin]["total_fees"] += partial_fee

                                _session[announcement_coin]["orders"].append(copy.deepcopy(_order[announcement_coin]))

                                logger.info(
                                    f"Partial fill order detected.  {order_status=} | "
                                    + f"{partial_amount=} out of {amount=} | {partial_fee=} | {price=}"
                                )
                                # FUTURE: We'll probably want to start attempting to sell in the future
                                # immediately after ordering any amount
                                # It would require at least a minor refactor, since order is getting cleared and
                                # it seems that this function depends on order being empty, but sell()
                                # depends on order not being empty.
                                # globals.sell_ready.set()

                            # order not filled, try again.
                            logger.info(f"Clearing order with a status of {order_status}.  Waiting for 'closed' status")
                            _order.pop(announcement_coin)  # reset for next iteration
                else:
                    logger.warning(
                        f"{announcement_coin=} is not supported on gate io", extra={"TELEGRAM": "COIN_NOT_SUPPORTED"}
                    )
                    logger.info(f"Adding {announcement_coin} to old_coins.json")
                    globals.old_coins.append(announcement_coin)
                    store_old_coins(globals.old_coins)
            else:
                logger.error("supported_currencies is not initialized")
        else:
            logger.info(
                "No coins announced, or coin has already been bought/sold. "
                + "Checking more frequently in case TP and SL need updating"
            )
        time.sleep(3)


def sell():
    while not globals.stop_threads:
        logger.debug("Waiting for sell_ready event")
        globals.sell_ready.wait()
        logger.debug("sell_ready event triggered")
        if globals.stop_threads:
            break
        # check if the order file exists and load the current orders
        # basically the sell block and update TP and SL logic
        if len(_order) > 0:
            for coin in list(_order):

                if float(_order[coin]["_tp"]) == 0:
                    st = _order[coin]["_status"]
                    logger.info(f"Order is initialized but not ready. Continuing. | Status={st}")
                    continue

                # store some necessary trade info for a sell
                coin_tp = _order[coin]["_tp"]
                coin_sl = _order[coin]["_sl"]

                volume = _order[coin]["_amount"]
                stored_price = float(_order[coin]["_price"])
                symbol = _order[coin]["_fee_currency"]

                # avoid div by zero error
                if float(stored_price) == 0:
                    continue

                logger.debug(
                    f"Data for sell: {coin=} | {stored_price=} | {coin_tp=} | {coin_sl=} | {volume=} | {symbol=} "
                )

                logger.info(f"get_last_price existing coin: {coin}")
                obj = get_last_price(symbol, globals.pairing, False)
                last_price = obj.price
                logger.info("Finished get_last_price")

                top_position_price = stored_price + (stored_price * coin_tp / 100)
                stop_loss_price = stored_price + (stored_price * coin_sl / 100)

                # need positive price or continue and wait
                if float(last_price) == 0:
                    continue

                logger.info(
                    f'{symbol=}-{last_price=}\t[STOP: ${"{:,.5f}".format(stop_loss_price)} or'
                    + f' {"{:,.2f}".format(coin_sl)}%]\t[TOP: ${"{:,.5f}".format(top_position_price)} or'
                    + f' {"{:,.2f}".format(coin_tp)}%]\t[BUY: ${"{:,.5f}".format(stored_price)} '
                    + f'(+/-): {"{:,.2f}".format(((float(last_price) - stored_price) / stored_price) * 100)}%]'
                )

                # update stop loss and take profit values if threshold is reached
                if float(last_price) > stored_price + (stored_price * coin_tp / 100) and globals.enable_tsl:
                    # increase as absolute value for TP
                    new_tp = float(last_price) + (float(last_price) * globals.ttp / 100)
                    # convert back into % difference from when the coin was bought
                    new_tp = float((new_tp - stored_price) / stored_price * 100)

                    # same deal as above, only applied to trailing SL
                    new_sl = float(last_price) + (float(last_price) * globals.tsl / 100)
                    new_sl = float((new_sl - stored_price) / stored_price * 100)

                    # new values to be added to the json file
                    _order[coin]["_tp"] = new_tp
                    _order[coin]["_sl"] = new_sl
                    store_order("order.json", _order)

                    new_top_position_price = stored_price + (stored_price * new_tp / 100)
                    new_stop_loss_price = stored_price + (stored_price * new_sl / 100)

                    logger.info(f'updated tp: {round(new_tp, 3)}% / ${"{:,.3f}".format(new_top_position_price)}')
                    logger.info(f'updated sl: {round(new_sl, 3)}% / ${"{:,.3f}".format(new_stop_loss_price)}')

                # close trade if tsl is reached or trail option is not enabled
                elif (
                    float(last_price) < stored_price + (stored_price * coin_sl / 100)
                    or float(last_price) > stored_price + (stored_price * coin_tp / 100)
                    and not globals.enable_tsl
                ):
                    try:
                        fees = float(_order[coin]["_fee"])
                        sell_volume_adjusted = float(volume) - fees

                        logger.info(
                            f"starting sell place_order with :{symbol} | {globals.pairing} | {volume} | "
                            + f"{sell_volume_adjusted} | {fees} | {float(sell_volume_adjusted)*float(last_price)} | "
                            + f"side=sell | last={last_price}",
                            extra={"TELEGRAM": "SELL_START"},
                        )

                        # sell for real if test mode is set to false
                        if not globals.test_mode:
                            sell = place_order(
                                symbol,
                                globals.pairing,
                                float(sell_volume_adjusted) * float(last_price),
                                "sell",
                                last_price,
                            )
                            logger.info("Finish sell place_order")

                            # check for completed sell order
                            if sell._status != "closed":

                                # change order to sell remaining
                                if float(sell._left) > 0 and float(sell._amount) > float(sell._left):
                                    # adjust down order _amount and _fee
                                    _order[coin]["_amount"] = sell._left
                                    _order[coin]["_fee"] = f"{fees - (float(sell._fee) / float(sell._price))}"

                                    # add sell order sold.json (handled better in session.json now)

                                    id = f"{coin}_{sell.id}"
                                    _sold_coins[id] = sell
                                    _sold_coins[id] = sell.__dict__
                                    _sold_coins[id].pop("local_vars_configuration")
                                    logger.info(
                                        f"Sell order did not close! {sell._left} of {coin} remaining."
                                        + " Adjusted order _amount and _fee to perform sell of remaining balance"
                                    )

                                    # add to session orders
                                    try:
                                        if len(_session) > 0:
                                            dp = copy.deepcopy(_sold_coins[id])
                                            _session[coin]["orders"].append(dp)
                                    except Exception as e:
                                        print(e)
                                    pass

                                # keep going.  Not finished until status is 'closed'
                                continue

                        logger.info(
                            f"sold {coin} with {round((float(last_price) - stored_price) * float(volume), 3)} profit"
                            + f" | {round((float(last_price) - stored_price) / float(stored_price)*100, 3)}% PNL",
                            extra={"TELEGRAM": "SELL_FILLED"},
                        )

                        # remove order from json file
                        _order.pop(coin)
                        store_order("order.json", _order)
                        logger.debug("Order saved in order.json")
                        globals.sell_ready.clear()

                    except Exception as e:
                        logger.error(e)

                    # store sold trades data
                    else:
                        if not globals.test_mode:
                            _sold_coins[coin] = sell
                            _sold_coins[coin] = sell.__dict__
                            _sold_coins[coin].pop("local_vars_configuration")
                            _sold_coins[coin]["profit"] = f"{float(last_price) - stored_price}"
                            _sold_coins[coin][
                                "relative_profit_%"
                            ] = f"{(float(last_price) - stored_price) / stored_price * 100}%"

                        else:
                            _sold_coins[coin] = {
                                "symbol": coin,
                                "price": last_price,
                                "volume": volume,
                                "time": datetime.timestamp(datetime.now()),
                                "profit": f"{float(last_price) - stored_price}",
                                "relative_profit_%": f"{(float(last_price) - stored_price) / stored_price * 100}%",
                                "id": "test-order",
                                "text": "test-order",
                                "create_time": datetime.timestamp(datetime.now()),
                                "update_time": datetime.timestamp(datetime.now()),
                                "currency_pair": f"{symbol}_{globals.pairing}",
                                "status": "closed",
                                "type": "limit",
                                "account": "spot",
                                "side": "sell",
                                "iceberg": "0",
                            }

                            logger.info(f"Sold coins:\r\n {_sold_coins[coin]}")

                        # add to session orders
                        try:
                            if len(_session) > 0:
                                dp = copy.deepcopy(_sold_coins[coin])
                                _session[coin]["orders"].append(dp)
                                store_order("session.json", _session)
                                logger.debug("Session saved in session.json")
                        except Exception as e:
                            print(e)
                            pass

                        store_order("sold.json", _sold_coins)
                        logger.info("Order saved in sold.json")
        else:
            logger.debug("Size of order is 0")
        time.sleep(3)


def load_sold_coins():
    global _sold_coins
    if os.path.isfile("sold.json"):
        _sold_coins = load_order("sold.json")


def load_orders():
    global _order
    if os.path.isfile("order.json"):
        _order = load_order("order.json")


def load_sessions():
    global _session
    # memory store for all orders for a specific coin
    if os.path.isfile("session.json"):
        _session = load_order("session.json")


def fetch_currencies():
    global _supported_currencies
    # Keep the supported currencies loaded in RAM so no time is wasted fetching
    # currencies.json from disk when an announcement is made
    logger.debug("Starting get_all_currencies")
    _supported_currencies = get_all_currencies(single=True)
    logger.debug("Finished get_all_currencies")


def main():
    """
    Sells, adjusts TP and SL according to trailing values
    and buys new coins
    """
    logger.info("started working...")

    # To add a coin to ignore, add it to the json array in old_coins.json
    globals.old_coins = load_old_coins()
    logger.debug(f"old_coins: {globals.old_coins}")

    # loads local configuration
    config = load_config("config.yml")

    # load necessary files
    load_old_coins()
    load_orders()
    load_sessions()

    fetch_currencies()

    logger.info("new-coin-bot online", extra={"TELEGRAM": "STARTUP"})

    # Protection from stale announcement
    latest_coin = get_last_coin()
    if latest_coin:
        globals.latest_listing = latest_coin

    # store config deets
    globals.quantity = config["TRADE_OPTIONS"]["QUANTITY"]
    globals.tp = config["TRADE_OPTIONS"]["TP"]
    globals.sl = config["TRADE_OPTIONS"]["SL"]
    globals.enable_tsl = config["TRADE_OPTIONS"]["ENABLE_TSL"]
    globals.tsl = config["TRADE_OPTIONS"]["TSL"]
    globals.ttp = config["TRADE_OPTIONS"]["TTP"]
    globals.pairing = config["TRADE_OPTIONS"]["PAIRING"]
    globals.test_mode = config["TRADE_OPTIONS"]["TEST"]

    globals.stop_threads = False
    globals.buy_ready.clear()

    if not globals.test_mode:
        logger.info("!!! LIVE MODE !!!")

    t_get_currencies_thread = threading.Thread(target=get_all_currencies)
    t_get_currencies_thread.start()
    t_buy_thread = threading.Thread(target=buy)
    t_buy_thread.start()
    t_sell_thread = threading.Thread(target=sell)
    t_sell_thread.start()

    try:
        search_and_update()
    except KeyboardInterrupt:
        logger.info("Stopping Threads")
        globals.stop_threads = True
        globals.buy_ready.set()
        globals.sell_ready.set()
        t_get_currencies_thread.join()
        t_buy_thread.join()
        t_sell_thread.join()

    logger.info("stopped working...")
