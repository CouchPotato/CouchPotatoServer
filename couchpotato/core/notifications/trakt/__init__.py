from .main import Trakt


def start():
    return Trakt()

config = [{
    'name': 'trakt',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'trakt',
            'label': 'Trakt',
            'description': 'add movies to your collection once downloaded. Fill in your username and password in the <a href="../automation/">Automation Trakt settings</a>',
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
            ],
        }
    ],
}]
