import yaml
import os
from gate_api import ApiClient, Configuration, Order, SpotApi

def load_gateio_creds(file):

    auth_vars = {
        "gateio_api": "GATE_IO_API_KEY",
        "gateio_secret": "GATE_IO_API_SECRET"
    }

    auth = {}

    if os.path.isfile(file):
        with open(file) as file:
            auth = yaml.load(file, Loader=yaml.FullLoader)

    for key, value in auth_vars.items():        
        if os.getenv(value) is not None:
            auth[key] = os.getenv(value)

        if auth[key] is None:
            raise Exception("Missing configuration: TRADE_OPTIONS: "+key)

    return Configuration(key=auth.gateio_api, secret=auth.gateio_secret)