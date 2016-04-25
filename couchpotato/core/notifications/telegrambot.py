from couchpotato.core.helpers.variable import getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import requests
import six

log = CPLog(__name__)

autoload = 'TelegramBot'

class TelegramBot(Notification):

    TELEGRAM_API = "https://api.telegram.org/bot%s/%s"

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        # Get configuration data
        token = self.conf('bot_token')
        usr_id = self.conf('receiver_user_id')

        # Add IMDB url to message:
        if data:
            imdb_id = getIdentifier(data)
            if imdb_id:
                url = 'http://www.imdb.com/title/{0}/'.format(imdb_id)
                message = '{0}\n{1}'.format(message, url)

        # Cosntruct message
        payload = {'chat_id': usr_id, 'text': message, 'parse_mode': 'Markdown'}

        # Send message user Telegram's Bot API
        response = requests.post(self.TELEGRAM_API % (token, "sendMessage"), data=payload)

        # Error logging
        sent_successfuly = True
        if not response.status_code == 200:
            log.error('Could not send notification to TelegramBot (token=%s). Response: [%s]', (token, response.text))
            sent_successfuly = False

        return sent_successfuly


config = [{
    'name': 'telegrambot',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'telegrambot',
            'label': 'Telegram Bot',
            'description': 'Notification provider which utilizes the bot API of the famous Telegram IM.',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'bot_token',
                    'description': 'Your bot token. Contact <a href="http://telegram.me/BotFather" target="_blank">@BotFather</a> on Telegram to get one.'
                },
                {
                    'name': 'receiver_user_id',
                    'label': 'Recieving User/Group ID',
                    'description': 'Receiving user/group - notifications will be sent to this user or group. Contact <a href="http://telegram.me/myidbot" target="_blank">@myidbot</a> on Telegram to get an ID.'
                },
                {
                    'name': 'on_snatch',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
            ],
        }
    ],
}]
