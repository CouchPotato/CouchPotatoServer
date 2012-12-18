from .main import Easynews


def start():
    return Easynews()

config = [{
    'name': 'nzbsrus',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'nzb_providers',
            'name': 'easynews',
            'label': 'Easynews',
            'description': 'Easynews global search',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'userid',
                    'label': 'User ID',
                },
                {
                    'name': 'password',
                    'label': 'Password',
                },
            ],
        },
    ],
}]
