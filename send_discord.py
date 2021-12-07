import logging
from discordwebhook import Discord
from load_config import *

config = load_config('config.yml')

with open('auth/auth.yml') as file:
    try:
        auth = yaml.load(file, Loader=yaml.FullLoader)
        discord_webhook_url = str(auth['discord_webhook_url'])
        valid_auth = True
    except KeyError:
        valid_auth = False
        pass


class DiscordLogFilter(logging.Filter):
    # filter for logRecords with DISCORD extra
    def filter(self, record):
        return hasattr(record, 'DISCORD')


class DiscordHandler(logging.Handler):
    # log to discord if the DISCORD extra matches an enabled key
    def emit(self, record):

        if not valid_auth:
            return

        key = getattr(record, 'DISCORD')

        # unknown message key
        if not key in config['DISCORD']['NOTIFICATIONS']:
            return

        # message key disabled
        if not config['DISCORD']['NOTIFICATIONS'][key]:
            return

        discord = Discord(url=discord_webhook_url)
        discord.post(content=record.message)

