import logging
from load_config import *


# loads local configuration
config = load_config('config.yml')

logger = logging

# Set default log settings
log_level = 'INFO'
log_file = 'bot.log'

# Get logging variables
log_level = config['LOGGING']['LOG_LEVEL']
log_file = config['LOGGING']['LOG_FILE']
logger.basicConfig(level=log_level, format='%(asctime)s %(levelname)s: %(message)s',
                   handlers=[logging.FileHandler(log_file), logging.StreamHandler()])

