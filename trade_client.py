from auth.gateio_auth import *
from gate_api import ApiClient, Configuration, Order, SpotApi

client = load_gateio_creds('auth/auth.yml')
spot_api = SpotApi(ApiClient(client))


def get_last_price(base,quote):
    """
    Args:
    'DOT', 'USDT'
    """
    tickers = spot_api.list_tickers(currency_pair=f'{base}_{quote}')
    assert len(tickers) == 1
    return tickers[0].last


def get_min_amount(base,quote):
    """
    Args:
    'DOT', 'USDT'
    """
    try:
        min_amount = spot_api.get_currency_pair(currency_pair=f'{base}_{quote}').min_quote_amount
    except Exception as e:
        print(e)
    else:
        return min_amount


def place_order(base,quote, amount, side, last_price):
    """
    Args:
    'DOT', 'USDT', 50, 'buy', 400
    """
    try:
        order = Order(amount="{:.4f}".format((float(400)/float(0.054543))), price=last_price, side=side, currency_pair=f'{base}_{quote}')
        order = spot_api.create_order(order)
    except Exception as e:
        print(e)
    else:
        return order
