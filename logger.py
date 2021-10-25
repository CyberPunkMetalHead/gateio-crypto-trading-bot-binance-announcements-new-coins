import logging
from load_config import *

import settings

# loads local configuration
config = load_config(settings.config_folder + '/config.yml')

log = logging

# Set default log settings
log_level = 'INFO'
log_file = settings.logs_folder + 'bot.log'

# Get logging variables
log_level = config['LOGGING']['LOG_LEVEL']
log_file = config['LOGGING']['LOG_FILE']
log.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
logger = logging.getLogger(__name__)
level = logging.getLevelName(log_level)
logger.setLevel(level)
