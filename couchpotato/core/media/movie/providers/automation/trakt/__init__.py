from .main import Trakt


def autoload():
    return Trakt()


config = [{
    'name': 'trakt',
    'groups': [
        {
            'tab': 'automation',
            'list': 'watchlist_providers',
            'name': 'trakt_automation',
            'label': 'Trakt',
            'description': 'Import movies from your own watchlist',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_oauth_token',
                    'label': 'Auth Token',
                    'advanced': 1
                },
            ],
        },
    ],
}]