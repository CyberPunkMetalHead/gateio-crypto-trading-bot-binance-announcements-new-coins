import logging
from load_config import *
from telegram_client import TelegramHandler, telegram_bot_sendtext


# loads local configuration
config = load_config('config.yml')

log = logging

# Set default log settings
log_level = 'INFO'
log_file = 'bot.log'

# Get logging variables
log_level = config['LOGGING']['LOG_LEVEL']
log_file = config['LOGGING']['LOG_FILE']
send_telegram = config['TELEGRAM']['SEND_MESSAGES']

if(send_telegram):
    log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                handlers=[logging.FileHandler(log_file), logging.StreamHandler(), TelegramHandler()])
else:
    log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
                
logger = logging.getLogger(__name__)
level = logging.getLevelName(log_level)
logger.setLevel(level)
