from .main import TheTVDb

def start():
    return TheTVDb()

config = [{
    'name': 'thetvdb',
    'groups': [
        {
            'tab': 'providers',
            'name': 'tmdb',
            'label': 'TheTVDB',
            'hidden': True,
            'description': 'Used for all calls to TheTVDB.',
            'options': [
                {
                    'name': 'api_key',
                    'default': '7966C02F860586D2',
                    'label': 'Api Key',
                },
            ],
        },
    ],
}]
