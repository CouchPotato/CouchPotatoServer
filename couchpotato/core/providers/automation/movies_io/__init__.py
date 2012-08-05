from .main import MoviesIO

def start():
    return MoviesIO()

config = [{
    'name': 'moviesio',
    'groups': [
        {
            'tab': 'automation',
            'name': 'moviesio',
            'label': 'Movies.IO',
            'description': 'Imports movies from <a href="http://movies.io">Movies.io</a> RSS watchlists',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_urls_use',
                    'label': 'Use',
                },
                {
                    'name': 'automation_urls',
                    'label': 'url',
                    'type': 'combined',
                    'combine': ['automation_urls_use', 'automation_urls'],
                },
            ],
        },
    ],
}]
