from logging import Handler, getLevelName
import requests
from load_config import *

class TelegramHandler(Handler):
    

    def emit(self, record):
        """
        Emit a record.

        If the stream was not opened because 'delay' was specified in the
        constructor, open it before calling the superclass's emit.
        """
        telegram_bot_sendtext(record)





def telegram_bot_sendtext(bot_message):
    config = load_config('auth/auth.yml')


    bot_token = config['telegram_token']
    bot_chatID = config['telegram_clientID']
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message.msg

    response = requests.get(send_text)

    return response.json()