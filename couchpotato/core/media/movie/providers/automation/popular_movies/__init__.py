from .main import PopularMovies

def start():
    return PopularMovies()

config = [{
    'name': 'popular_movies',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'popular_movies_automation',
            'label': 'Popular Movies',
            'description': 'Imports the top titles of movies that have been in theaters.',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
            ],
        },
    ],
}]
