import os
import yaml


def load_config(file):

    config = {}

    if os.path.isfile(file):
        with open(file) as file:
            config = yaml.load(file, Loader=yaml.FullLoader)

    config_mapping = {
        'TRADE_OPTIONS': {
            'TP':'TRADE_TP',
            'SL':'TRADE_SL',
            'ENABLE_TSL':'TRADE_ENABLE_TSL',
            'TSL':'TRADE_TSL',
            'TTP':'TRADE_TTP',
            'PAIRING':'TRADE_PAIRING',
            'QUANTITY':'TRADE_QUANTITY',
            'RUN_EVERY':'TRADE_RUN_EVERY',
            'TEST':'TRADE_TEST'
        },
        'LOGGING': {
            'LOG_LEVEL':'LOG_LEVEL',
            'LOG_FILE':'LOG_FILE',
        },
    }


    for section_key, sectionsettings in config_mapping.items():

        if not hasattr(config, section_key):
            config[section_key] = {}

        for setting_key, setting_env_var_name in sectionsettings.items():  
            if os.getenv(setting_env_var_name) is not None:
                config[section_key][setting_key] = os.getenv(setting_env_var_name)
                print("Setting from env_var: "+section_key+"/"+setting_key+": "+config[section_key][setting_key])

            try:
                config[section_key][setting_key]
                pass
            except KeyError:
                raise Exception("Missing configuration: "+section_key+"/"+setting_key)

    return config


    