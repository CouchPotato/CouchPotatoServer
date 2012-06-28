from .main import Queue

def start():
    return Queue()

config = [{
    'name': 'Queue',
    'groups': [
        {
            'tab': 'queue',
            'label': 'queue library manager',
            'description': 'Show details of the move in your downloader.',
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'enabler',
                },
            ],
        },
    ],
}]
