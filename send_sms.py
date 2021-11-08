from logging import log
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from logger import logger
from auth.twilio_auth import *

import yaml

keys = load_twilio_creds('auth/auth_twilio.yml')

account_sid = keys['twilio_account_sid']
auth_token  = keys['twilio_auth_token']
to_number = keys['twilio_to_number']
from_number = keys['twilio_from_number']

client = Client(account_sid, auth_token)

def send_sms_message(body):
    try:

        message = client.messages.create(
            to=to_number, 
            from_=from_number,
            body=body)

        logger.info(f'SMS sent: {message.sid=}')

    except TwilioRestException as e:
       logger.debug(e)

