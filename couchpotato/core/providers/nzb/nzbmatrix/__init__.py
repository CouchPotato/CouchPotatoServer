from .main import NZBMatrix

def start():
    return NZBMatrix()

config = [{
    'name': 'nzbmatrix',
    'groups': [
        {
            'tab': 'providers',
            'name': 'nzbmatrix',
            'label': 'NZBMatrix',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'username',
                },
                {
                    'name': 'api_key',
                    'default': '',
                    'label': 'Api Key',
                },
            ],
        },
    ],
}]
