from .main import TheMovieDb


def start():
    return TheMovieDb()

config = [{
    'name': 'themoviedb',
    'groups': [
        {
            'tab': 'providers',
            'name': 'tmdb',
            'label': 'TheMovieDB',
            'hidden': True,
            'description': 'Used for all calls to TheMovieDB.',
            'options': [
                {
                    'name': 'api_key',
                    'default': '9b939aee0aaafc12a65bf448e4af9543',
                    'label': 'Api Key',
                },
            ],
        },
        {
            'tab': 'searcher',
            'name': 'searcher',
            'label': 'Basics',
            'description': 'General search options',
            'options': [
                {
                    'name': 'lang',
                    'label': 'Language',
                    'description': 'Countrycode used for fetching alternate Titles',
                    'default': 'US',
                },
            ],
        },
    ],
}]
