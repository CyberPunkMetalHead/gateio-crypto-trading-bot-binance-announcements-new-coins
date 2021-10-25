import os
import yaml


def load_config(file):

    # read env vars first

    config =  {
        'TRADE_OPTIONS':{
            'TP':os.getenv('TRADE_TP'),
            'SL':os.getenv('TRADE_SL'),
            'ENABLE_TSL':os.getenv('TRADE_ENABLE_TSL'),
            'TSL':os.getenv('TRADE_TSL'),
            'TTP':os.getenv('TRADE_TTP'),
            'PAIRING':os.getenv('TRADE_PAIRING'),
            'QUANTITY':os.getenv('TRADE_QUANTITY'),
            'RUN_EVERY':os.getenv('TRADE_RUN_EVERY'),
            'TEST':os.getenv('TRADE_TEST')
        }
    }

    # read file if existing

    if os.path.isfile(file):
        with open(file) as file:
            config = yaml.load(file, Loader=yaml.FullLoader)

    return config


    