from .main import Trakt


def start():
    return Trakt()

config = [{
    'name': 'trakt',
    'groups': [
        {
            'tab': 'automation',
            'list': 'watchlist_providers',
            'name': 'trakt_automation',
            'label': 'Trakt',
            'description': 'import movies from your own watchlist',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
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
                    'description': 'When you have "Protect my data" checked <a href="http://trakt.tv/settings/account">on trakt</a>.',
                },
            ],
        },
    ],
}]
