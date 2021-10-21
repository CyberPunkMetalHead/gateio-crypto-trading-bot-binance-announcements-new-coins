import json
import os


def store_order(file, order):
    """
    Save order into local json file
    """
    with open(file, 'w') as f:
        json.dump(order, f, indent=4)


def load_order(file):
    """
    Update Json file
    """
    if not os.path.isfile(file) or os.stat(file).st_size == 0:
        return {}
    with open(file, "r+") as f:
        return json.load(f)
