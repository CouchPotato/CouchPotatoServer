import json
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification

log = CPLog(__name__)
autoload = 'Slack'


class Slack(Notification):
    url = 'https://slack.com/api/chat.postMessage'
    required_confs = ('token', 'channels',)

    def notify(self, message='', data=None, listener=None):
        for key in self.required_confs:
            if not self.conf(key):
                log.warning('Slack notifications are enabled, but '
                            '"{0}" is not specified.'.format(key))
                return False

        data = data or {}
        message = message.strip()

        if self.conf('include_imdb') and 'identifier' in data:
            template = ' http://www.imdb.com/title/{0[identifier]}/'
            message += template.format(data)

        payload = {
            'token': self.conf('token'),
            'text': message,
            'username': self.conf('bot_name'),
            'unfurl_links': self.conf('include_imdb'),
            'as_user': self.conf('as_user'),
            'icon_url': self.conf('icon_url'),
            'icon_emoji': self.conf('icon_emoji')
        }

        channels = self.conf('channels').split(',')
        for channel in channels:
            payload['channel'] = channel.strip()
            response = self.urlopen(self.url, data=payload)
            response = json.loads(response)
            if not response['ok']:
                log.warning('Notification sending to Slack has failed. Error '
                            'code: %s.', response['error'])
                return False
        return True


config = [{
    'name': 'slack',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'slack',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'token',
                    'description': (
                        'Your Slack authentication token.',
                        'Can be created at https://api.slack.com/web'
                    )
                },
                {
                    'name': 'channels',
                    'description': (
                        'Channel to send notifications to.',
                        'Can be a public channel, private group or IM '
                        'channel. Can be an encoded ID or a name '
                        '(staring with a hashtag, e.g. #general). '
                        'Separate with commas in order to notify multiple '
                        'channels. It is however recommended to send '
                        'notifications to only one channel due to '
                        'the Slack API rate limits.'
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
                    'name': 'as_user',
                    'description': 'Send message as the authentication token '
                                   ' user.',
                    'default': False,
                    'type': 'bool',
                    'advanced': True
                },
                {
                    'name': 'icon_url',
                    'description': 'URL to an image to use as the icon for '
                                   'notifications.',
                    'advanced': True,
                },
                {
                    'name': 'icon_emoji',
                    'description': (
                        'Emoji to use as the icon for notifications.',
                        'Overrides icon_url'
                    ),
                    'advanced': True,
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
