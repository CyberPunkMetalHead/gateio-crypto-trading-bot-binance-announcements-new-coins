import yaml

def load_twilio_creds(file):
    with open(file) as file:
        auth = yaml.load(file, Loader=yaml.FullLoader)

    return auth
