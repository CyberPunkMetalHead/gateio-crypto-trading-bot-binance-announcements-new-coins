import os
import logging
from load_config import *
from send_telegram import *
from logging.handlers import TimedRotatingFileHandler

# loads local configuration
config = load_config('config.yml')

log = logging

# Set default log settings
log_level = 'INFO'
cwd = os.getcwd()
log_dir = "logs"
log_file = 'bot.log'
log_to_console = True
log_path = os.path.join(cwd, log_dir, log_file)

# create logging directory
if not os.path.exists(log_dir):
    os.mkdir(log_dir)

# Get logging variables
log_level = config['LOGGING']['LOG_LEVEL']
log_file = config['LOGGING']['LOG_FILE']

try:
    log_telegram = config['TELEGRAM']['ENABLED']
except KeyError:
    pass

try:
    log_to_console = config['LOGGING']['LOG_TO_CONSOLE']
except KeyError:
    pass

file_handler = TimedRotatingFileHandler(log_path, when="midnight")
handlers = [file_handler]
if log_to_console:
    handlers.append(logging.StreamHandler())
if log_telegram:
    telegram_handler = TelegramHandler()
    telegram_handler.addFilter(TelegramLogFilter()) # only handle messages with extra: TELEGRAM
    telegram_handler.setLevel(logging.NOTSET)  # so that telegram can recieve any kind of log message
    handlers.append(telegram_handler)

log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                handlers=handlers)

logger = logging.getLogger(__name__)
level = logging.getLevelName(log_level)
logger.setLevel(level)
