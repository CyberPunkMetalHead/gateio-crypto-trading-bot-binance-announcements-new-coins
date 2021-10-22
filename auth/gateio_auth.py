import yaml
from gate_api import ApiClient, Configuration, Order, SpotApi
from load_config import *

def load_gateio_creds(file):
    try:
        with open(file) as file:
            auth = yaml.load(file, Loader=yaml.FullLoader)
            return Configuration(key=auth['gateio_api'], secret=auth['gateio_secret'])
    except FileNotFoundError as e:
        # if auth config doesn't exist, query user if they want help
        create_config(file)
        raise FileNotFoundError("check that your "+file+" exists, use "+file.split(".")[0]+
                                ".example.yml as a template. e: " + str(e))
