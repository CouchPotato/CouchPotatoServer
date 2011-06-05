from .main import Nzbget

def start():
    return Nzbget()

config = [{
    'name': 'nzbget',
    'groups': [
        {
            'tab': 'downloaders',
            'name': 'nzbget',
            'label': 'NZBGet',
            'description': 'Send NZBs to your NZBGet installation.',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'host',
                    'default': 'localhost:6789',
                },
                {
                    'name': 'category',
                    'default': 'movies',
                },
                {
                    'name': 'password',
                    'type': 'password',
                    'description': 'If your installation doesn\'t require a password, keep this blank.',
                },
            ],
        }
    ],
}]
