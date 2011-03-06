from couchpotato.core.providers.tmdb.main import TMDB

def start():
    return TMDB()

config = [{
    'name': 'themoviedb',
    'groups': [
        {
            'tab': 'providers',
            'name': 'tmdb',
            'label': 'TheMovieDB',
            'advanced': True,
            'options': [
                {
                    'name': 'api_key',
                    'default': '9b939aee0aaafc12a65bf448e4af9543',
                    'type': 'string',
                    'label': 'Api Key',
                    'description': 'Used for all calls to TheMovieDB.',
                },
            ],
        },
    ],
}]
