from couchpotato.core.plugins.renamer.main import Renamer

def start():
    return Renamer()

config = [{
    'name': 'renamer',
    'groups': [
        {
            'tab': 'renamer',
            'name': 'tmdb',
            'label': 'TheMovieDB',
            'advanced': True,
            'description': 'Move and rename your downloaded movies to your movie directory.',
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'from',
                    'type': 'directory',
                    'description': 'Folder where the movies are downloaded to.',
                },
                {
                    'name': 'to',
                    'type': 'directory',
                    'description': 'Folder where the movies will be moved to.',
                },
                {
                    'name': 'run_every',
                    'label': 'Run every',
                    'default': 1,
                    'type': 'int',
                    'unit': 'min(s)',
                    'description': 'Search for new movies inside the folder every X minutes.',
                }
            ],
        },
    ],
}]
