import yaml
import os
from gate_api import ApiClient, Configuration, Order, SpotApi

def load_gateio_creds(file):

    # read env vars first

    auth = {
        'gateio_api':os.getenv('GATE_IO_API_KEY'),
        'gateio_secret':os.getenv('GATE_IO_API_SECRET')
    }

    # read file if existing

    if os.path.isfile(file):
        with open(file) as file:
            auth = yaml.load(file, Loader=yaml.FullLoader)

    return Configuration(key=auth['gateio_api'], secret=auth['gateio_secret'])