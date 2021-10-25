import os
import yaml


def load_config(file):

    config = {}

    if os.path.isfile(file):
        with open(file) as file:
            config = yaml.load(file, Loader=yaml.FullLoader)

    config_vars = {
            'TP':'TRADE_TP',
            'SL':'TRADE_SL',
            'ENABLE_TSL':'TRADE_ENABLE_TSL',
            'TSL':'TRADE_TSL',
            'TTP':'TRADE_TTP',
            'PAIRING':'TRADE_PAIRING',
            'QUANTITY':'TRADE_QUANTITY',
            'RUN_EVERY':'TRADE_RUN_EVERY',
            'TEST':'TRADE_TEST'
    }

    for key, value in config_vars.items():        
        if os.getenv(value) is not None:
            config['TRADE_OPTIONS'][key] = os.getenv(value)

        if config['TRADE_OPTIONS'][key] is None:
            raise Exception("Missing configuration: TRADE_OPTIONS: "+key)

    return config


    