from .main import Email


def start():
    return Email()

config = [{
    'name': 'email',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'email',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'from',
                    'label': 'Send e-mail from',
                },
                {
                    'name': 'to',
                    'label': 'Send e-mail to',
                },
                {
                    'name': 'smtp_server',
                    'label': 'SMTP server',
                },
                {   'name': 'smtp_port',
                    'label': 'SMTP server port',
                    'default': '25',
                    'type': 'int',
                },
                {
                    'name': 'ssl',
                    'label': 'Enable SSL',
                    'default': 0,
                    'type': 'bool',
                },
                {
                    'name': 'starttls',
                    'label': 'Enable StartTLS',
                    'default': 0,
                    'type': 'bool',
                },
                {
                    'name': 'smtp_user',
                    'label': 'SMTP user',
                },
                {
                    'name': 'smtp_pass',
                    'label': 'SMTP password',
                    'type': 'password',
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
