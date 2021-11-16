from datetime import datetime
from logger import logger

from auth.gateio_auth import *
from gate_api import ApiClient, Order, SpotApi

client = load_gateio_creds('auth/auth.yml')
spot_api = SpotApi(ApiClient(client))

current_last_trade = None


def get_last_price(base, quote, return_price_only):
    """
    Args:
    'DOT', 'USDT'
    """
    global current_last_trade
    trades = spot_api.list_trades(currency_pair=f'{base}_{quote}', limit=1)
    assert len(trades) == 1
    t = trades[0]

    create_time_ms = datetime.utcfromtimestamp(int(t.create_time_ms.split('.')[0]) / 1000)
    create_time_formatted = create_time_ms.strftime('%d-%m-%y %H:%M:%S.%f')

    if current_last_trade and current_last_trade.id > t.id:
        logger.debug(f"CACHED TRADEBOOK RESULT FOUND. RE-TRYING.")
        return get_last_price(base=base, quote=quote, return_price_only=return_price_only)
    else:
        current_last_trade = t

    if return_price_only:
        return t.price

    logger.info(f"LATEST TRADE: {t.currency_pair} | id={t.id} | create_time%={create_time_formatted} | "
                f"side={t.side} | amount={t.amount} | price={t.price}")
    return t


def get_min_amount(base, quote):
    """
    Args:
    'DOT', 'USDT'
    """
    try:
        min_amount = spot_api.get_currency_pair(currency_pair=f'{base}_{quote}').min_quote_amount
    except Exception as e:
        logger.error(e)
    else:
        return min_amount


def place_order(base, quote, amount, side, last_price):
    """
    Args:
    'DOT', 'USDT', 50, 'buy', 400
    """
    try:
        order = Order(amount=str(float(amount) / float(last_price)), price=last_price, side=side,
                      currency_pair=f'{base}_{quote}', time_in_force='ioc')
        order = spot_api.create_order(order)
        t = order
        logger.info(
            f"PLACE ORDER: {t.side} | {t.id} | {t.account} | {t.type} | {t.currency_pair} | {t.status} | "
            f"amount={t.amount} | price={t.price} | left={t.left} | filled_total={t.filled_total} | "
            f"fill_price={t.fill_price} | fee={t.fee} {t.fee_currency}")
    except Exception as e:
        logger.error(e)
        raise

    else:
        return order
