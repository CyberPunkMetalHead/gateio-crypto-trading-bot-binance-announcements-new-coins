import yaml
from gate_api import ApiClient, Configuration, Order, SpotApi


def load_gateio_creds(file):
    with open(file) as file:
        auth = yaml.load(file, Loader=yaml.FullLoader)

    return Configuration(key=auth['gateio_api'], secret=auth['gateio_secret'])
