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
    ],
    'groups': [
        {
            'tab': 'searcher',
            'name': 'searcher',
            'label': 'Search',
            'description': 'Options for the searchers',
            'options': [
                {
                    'name': 'search_language',
                    'label': 'Language',
                    'default': 'en',
                    'description': 'Language for movie\'s title (if possible, English otherwise)',
		    'type': 'dropdown',
		    'values': [('English', 'en'), ('Czech', 'cs'), ('Danish', 'da'), ('German', 'de'), ('Spanish', 'es'), ('Finnish', 'fi'), ('French', 'fr'), ('Hebrew', 'he'), ('Hungarian', 'hu'), ('Italian', 'it'), ('Dutch', 'nl'), ('Polish', 'pl'), ('Portuguese', 'pt'), ('Russian', 'ru'), ('Swedish', 'sv'), ('Turkish', 'tr'), ('Ukrainian', 'uk'), ('Chinese', 'zh')],
                },
	   ],
       },
    ],
}]
