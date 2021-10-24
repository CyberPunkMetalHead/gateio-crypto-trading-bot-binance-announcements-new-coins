import sys

import yaml
import os.path
import shutil


def load_config(file_name):
    try:
        with open(file_name) as file:
            #grab config file
            config = yaml.load(file, Loader=yaml.FullLoader)

            #since we're here, notify user of testing status so they know if they're using money or not
            if config['TRADE_OPTIONS']['TEST']:
                print("*** NOTICE: YOU ARE IN TEST MODE ***")
            else:
                print("*** NOTICE: YOU ARE LIVE. CONTACTING GATEIO API ***")

            return config

    except FileNotFoundError as e:
        #if config doesn't exist, query user if they want help
        create_config(file_name)
        raise FileNotFoundError("check that your "+file_name+" exists, use "
                                +file_name.split(".")[0]+".example.yml as a template. e: " + str(e))


# maybe we can lend them a hand, and make the file for them if they need it
def create_config(config_name, subdirectory=None):

    example_filename = config_name.split(".")[0]+".example.yml"

    if not os.path.isfile(example_filename):
        print("checked for bundled example file : " + example_filename + " couldn't find it either. aborting..")
        return

    prompt = input("the config file: " + config_name + " doesn't exist, do you want it to be created with default values? (y/n):")

    #invalid input
    if prompt.lower() != 'y' and prompt.lower() != 'n':
        print("you didn't type y or n, aborting..")
        sys.exit()

    #if user wants file made for them
    if prompt.lower() == 'y':
        path = os.getcwd()

        if subdirectory is not None:
            path = os.path.join(path, subdirectory)

        #copy example file to desired non-example name
        shutil.copyfile(os.path.join(path, example_filename), os.path.join(path, config_name))
        print("generated file: " + config_name + " please take a look at the values, then re-run the application")

    sys.exit()

