from .main import Prowl

def start():
    return Prowl()

config = [{
    'name': 'prowl',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'prowl',
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'enabler',
                    'description': '',
                },
                {
                    'name': 'api_key',
                    'default': '',
                    'label': 'Api key',
                    'description': '',
                },
                {
                    'name': 'priority',
                    'default': '0',
                    'type': 'dropdown',
                    'description': '',
                    'values': [('Very Low', -2), ('Moderate', -1), ('Normal', 0), ('High', 1), ('Emergency', 2)]
                },
            ],
        }
    ],
}]
