import logging
import os
from logging.handlers import TimedRotatingFileHandler

from gateio_new_coins_announcements_bot.load_config import load_config
from gateio_new_coins_announcements_bot.send_telegram import TelegramHandler
from gateio_new_coins_announcements_bot.send_telegram import TelegramLogFilter

_logger = None


def init_logger():
    global _logger

    # loads local configuration
    config = load_config("config.yml")

    # Set default log settings
    log_level = "INFO"
    cwd = os.getcwd()
    log_dir = "logs"
    log_file = "bot.log"
    log_to_console = True
    log_path = os.path.join(cwd, log_dir, log_file)

    # create logging directory
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    # Get logging variables
    log_level = config["LOGGING"]["LOG_LEVEL"]
    log_file = config["LOGGING"]["LOG_FILE"]

    try:
        log_telegram = config["TELEGRAM"]["ENABLED"]
    except KeyError:
        pass

    try:
        log_to_console = config["LOGGING"]["LOG_TO_CONSOLE"]
    except KeyError:
        pass

    file_handler = TimedRotatingFileHandler(log_path, when="midnight")
    handlers = [file_handler]
    if log_to_console:
        handlers.append(logging.StreamHandler())
    if log_telegram:
        telegram_handler = TelegramHandler()
        telegram_handler.addFilter(TelegramLogFilter())  # only handle messages with extra: TELEGRAM
        telegram_handler.setLevel(logging.NOTSET)  # so that telegram can recieve any kind of log message
        handlers.append(telegram_handler)

    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", handlers=handlers)

    _logger = logging.getLogger(__name__)
    level = logging.getLevelName(log_level)
    _logger.setLevel(level)


def _LOG_FUNCTION(log_level, *args, telegram_key=None):
    """
    Logs the message with the given log_level. If telegram_key is not None, the message will be sent to telegram as well
    """
    if telegram_key is not None:
        if type(telegram_key) is str:
            _logger.log(log_level, *args, extra={"TELEGRAM": telegram_key})
        else:
            raise TypeError("telegram_key must be a string or None")
    else:
        _logger.log(log_level, *args)


# Currently not used
# def LOG_CRITICAL(*args, telegram_key=None):
#     '''
#     Logs the message with CRITICAL level. If telegram_key is not None, the message will be sent to telegram as well
#     '''
#     __LOG_FUNCTION(logging.CRITICAL, *args, telegram_key=telegram_key)


def LOG_ERROR(*args, telegram_key=None):
    """
    Logs the message with ERROR level. If telegram_key is not None, the message will be sent to telegram as well
    """
    _LOG_FUNCTION(logging.ERROR, *args, telegram_key=telegram_key)


# Currently not used
# def LOG_WARNING(*args, telegram_key=None):
#     '''
#     Logs the message with WARNING level. If telegram_key is not None, the message will be sent to telegram as well
#     '''
#     __LOG_FUNCTION(logging.WARNING, *args, telegram_key=telegram_key)


def LOG_INFO(*args, telegram_key=None):
    """
    Logs the message with INFO level. If telegram_key is not None, the message will be sent to telegram as well
    """
    _LOG_FUNCTION(logging.INFO, *args, telegram_key=telegram_key)


def LOG_DEBUG(*args, telegram_key=None):
    """
    Logs the message with DEBUG level. If telegram_key is not None, the message will be sent to telegram as well
    """
    _LOG_FUNCTION(logging.DEBUG, *args, telegram_key=telegram_key)
