from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import json
import requests

log = CPLog(__name__)
autoload = 'Discord'


class Discord(Notification):
    required_confs = ('webhook_url',)

    def notify(self, message='', data=None, listener=None):
        for key in self.required_confs:
            if not self.conf(key):
                log.warning('Discord notifications are enabled, but '
                            '"{0}" is not specified.'.format(key))
                return False

        data = data or {}
        message = message.strip()

        if self.conf('include_imdb') and 'identifier' in data:
            template = ' http://www.imdb.com/title/{0[identifier]}/'
            message += template.format(data)

        headers = {b"Content-Type": b"application/json"}
        try:
            r = requests.post(self.conf('webhook_url'), data=json.dumps(dict(content=message, username=self.conf('bot_name'), avatar_url=self.conf('avatar_url'), tts=self.conf('discord_tts'))), headers=headers)
            r.status_code
        except Exception as e:
            log.warning('Error Sending Discord response error code: {0}'.format(r.status_code))
            return False
        return True


config = [{
    'name': 'discord',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'discord',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'webhook_url',
                    'description': (
                        'Your Discord authentication webhook URL.',
                        'Created under channel settings.'
                    )
                },
                {
                    'name': 'include_imdb',
                    'default': True,
                    'type': 'bool',
                    'descrpition': 'Include a link to the movie page on IMDB.'
                },
                {
                    'name': 'bot_name',
                    'description': 'Name of bot.',
                    'default': 'CouchPotato',
                    'advanced': True,
                },
                {
                    'name': 'avatar_url',
                    'description': 'URL to an image to use as the avatar for '
                                   'notifications.',
                    'default': 'https://couchpota.to/media/images/couch.png',
                    'advanced': True,
                },
                {
                    'name': 'discord_tts',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Send notification using text-to-speech.',
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
