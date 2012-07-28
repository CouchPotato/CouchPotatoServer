from .main import Plex

def start():
    return Plex()

config = [{
    'name': 'plex',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'plex',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'server_host',
                    'default': 'localhost:32400',
                    'description': 'Specify the host and port for Plex Media Server.  This is used to notify PMS to rescan it\'s library.',
                    'advanced': True,
                },
                {
                    'name': 'client_host',
                    'default': 'localhost:3000',
                    'description': 'Specify the host and port for Plex Media Center.  This is used to display an on-screen notification in PMC.',
                    'advanced': True,
                },
            ],
        }
    ],
}]
