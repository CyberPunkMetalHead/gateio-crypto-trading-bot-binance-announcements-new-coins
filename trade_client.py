from logger import logger

from auth.gateio_auth import *
from gate_api import ApiClient, Configuration, Order, SpotApi

client = load_gateio_creds('auth/auth.yml')
spot_api = SpotApi(ApiClient(client))


def get_coin_info(base,quote):
    """
    Args:
    'DOT', 'USDT'
    """
    tickers = spot_api.list_tickers(currency_pair=f'{base}_{quote}')
    return tickers[0]


def get_min_amount(base,quote):
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


def place_order(base,quote, amount, side, last_price):
    """
    Args:
    'DOT', 'USDT', 50, 'buy', 400
    """
    try:
        order = Order(amount=str(float(amount)/float(last_price)), price=last_price, side=side, currency_pair=f'{base}_{quote}', time_in_force='ioc')
        order = spot_api.create_order(order)
        t = order
        logger.info(f"PLACE ORDER: {t.side} | {t.id} | {t.account} | {t.type} | {t.currency_pair} | {t.status} | amount={t.amount} | price={t.price} | left={t.left} | filled_total={t.filled_total} | fill_price={t.fill_price}")
    except Exception as e:
        logger.error(e)
        raise

    else:
        return order
