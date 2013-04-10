from .main import Manage

def start():
    return Manage()

config = [{
    'name': 'manage',
    'groups': [
        {
            'tab': 'manage',
            'label': 'Movie Library Manager',
            'description': 'Add your existing movie folders.',
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'library',
                    'type': 'directories',
                    'description': 'Folder where the movies should be moved to.',
                },
                {
                    'label': 'Cleanup After',
                    'name': 'cleanup',
                    'type': 'bool',
                    'description': 'Remove movie from db if it can\'t be found after re-scan.',
                    'default': True,
                },
            ],
        },
    ],
}]
