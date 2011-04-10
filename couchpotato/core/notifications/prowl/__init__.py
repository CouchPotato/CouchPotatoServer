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
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'api_key',
                    'label': 'Api key',
                },
                {
                    'name': 'priority',
                    'default': '0',
                    'type': 'dropdown',
                    'values': [('Very Low', -2), ('Moderate', -1), ('Normal', 0), ('High', 1), ('Emergency', 2)]
                },
            ],
        }
    ],
}]
