import os
import logging
from load_config import *
from logging.handlers import TimedRotatingFileHandler


# loads local configuration
config = load_config('config.yml')

log = logging

# Set default log settings
log_level = 'INFO'
cwd = os.getcwd()
log_dir = "logs"
log_file = 'bot.log'
log_path = os.path.join(cwd, log_dir, log_file)

# create logging directory
if not os.path.exists(log_dir):
    os.mkdir(log_dir)

# Get logging variables
log_level = config['LOGGING']['LOG_LEVEL']
log_file = config['LOGGING']['LOG_FILE']

file_handler = TimedRotatingFileHandler(log_path, when="midnight")
log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                handlers=[file_handler])
logger = logging.getLogger(__name__)
level = logging.getLevelName(log_level)
logger.setLevel(level)
