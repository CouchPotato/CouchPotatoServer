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
                    'default': '9b939aee0aaafc12a65bf448e4af9543',
                    'label': 'Api Key',
                },
            ],
        },
    ],
}]
