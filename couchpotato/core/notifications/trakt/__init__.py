from .main import Trakt

def start():
    return Trakt()

config = [{
    'name': 'trakt',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'trakt_notification',
            'label': 'Trakt',
            'description': 'add movies to your collection once downloaded',
            'options': [
                {
                    'name': 'notification_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'remove_watchlist_enabled',
                    'label': 'Remove from watchlist',
                    'default': False,
                    'type': 'bool',
                },
                {
                    'name': 'automation_api_key',
                    'label': 'Apikey',
                },
                {
                    'name': 'automation_username',
                    'label': 'Username',
                },
                {
                    'name': 'automation_password',
                    'label': 'Password',
                    'type': 'password',
                    'description': 'Required even if your account is unprotected.',
                },
            ],
        }
    ],
}]