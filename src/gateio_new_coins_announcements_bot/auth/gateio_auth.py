import yaml
import os
from gate_api import Configuration


def load_gateio_creds(file):
    with open(file) as file:
        auth = yaml.load(file, Loader=yaml.FullLoader)

    api_key = os.getenv("GATEIO_API") or auth["gateio_api"]
    api_secret = os.getenv("GATEIO_SECRET") or auth["gateio_secret"]

    return Configuration(key=api_key, secret=api_secret)
