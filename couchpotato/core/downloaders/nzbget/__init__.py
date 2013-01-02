from .main import NZBGet

def start():
    return NZBGet()

config = [{
    'name': 'nzbget',
    'groups': [
        {
            'tab': 'downloaders',
            'name': 'nzbget',
            'label': 'NZBGet',
            'description': 'Use <a href="http://nzbget.sourceforge.net/Main_Page" target="_blank">NZBGet</a> to download NZBs.',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'nzb',
                },
                {
                    'name': 'host',
                    'default': 'localhost:6789',
                    'description': 'Hostname with port. Usually <strong>localhost:6789</strong>',
                },
                {
                    'name': 'password',
                    'type': 'password',
                    'description': 'Default NZBGet password is <i>tegbzn6789</i>',
                },
                {
                    'name': 'category',
                    'default': 'Movies',
                    'description': 'The category CP places the nzb in. Like <strong>movies</strong> or <strong>couchpotato</strong>',
                },
                {
                    'name': 'manual',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Disable this downloader for automated searches, but use it when I manually send a release.',
                },
            ],
        }
    ],
}]
