from .main import Xmpp

def start():
    return Xmpp()

config = [{
    'name': 'xmpp',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'xmpp',
            'label': 'XMPP',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'username',
                    'description': 'User sending the message. For Hangouts, e-mail of a single-step authentication Google account.',
                },
                {
                    'name': 'password',
                    'type': 'Password',
                },
                {
                    'name': 'hostname',
                    'default': 'talk.google.com',
                },
                {
                    'name': 'use_tls',
                    'label': 'Use TLS',
                    'type': 'bool',
                    'default': 1,
                    'advanced': True,
                },
                {
                    'name': 'use_ssl',
                    'label': 'Use SSL',
                    'type': 'bool',
                    'advanced': True,
                },
                {
                    'name': 'to',
                    'description': 'Username (or e-mail for Hangouts) of the person to send the messages to.',
                },
                {
                    'name': 'port',
                    'type': 'int',
                    'default': 5222,
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
