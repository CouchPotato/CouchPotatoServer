from .main import CP

def start():
    return CP()

config = [{
    'name': 'cp',
    'groups': [
        {
            'tab': 'automation',
            'name': 'couchpotato_automation',
            'label': 'CouchPotato',
            'description': 'Enable automatic movie adding from CouchPotato',
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
