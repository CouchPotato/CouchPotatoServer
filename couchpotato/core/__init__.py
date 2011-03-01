from uuid import uuid4

def start():
    pass

config = [{
    'name': 'global',
    'tab': 'general',
    'options': {
        'debug': {
            'advanced': True,
            'default': False,
            'type': 'bool',
            'label': 'Debug',
            'description': 'Enable debugging.',
        },
        'host': {
            'advanced': True,
            'default': '0.0.0.0',
            'type': 'string',
            'label': 'Host',
            'description': 'Host that I should listen to 0.0.0.0 listens to everything.',
        },
        'port': {
            'default': 5000,
            'type': 'int',
            'label': 'Port',
            'description': 'The port I should listen to.',
        },
        'username': {
            'default': '',
            'type': 'string',
            'label': 'Username',
        },
        'password': {
            'default': '',
            'password': True,
            'type': 'string',
            'label': 'Password',
        },
        'launch_browser': {
            'default': True,
            'type': 'bool',
            'label': 'Launch Browser',
            'description': 'Launch the browser when I start.',
        },
        'url_base': {
            'advanced': True,
            'default': '',
            'type': 'string',
            'label': 'Url Base',
            'description': 'When using mod_proxy use this to prepend the url with this.',
        },
        'api_key': {
            'default': uuid4().hex,
            'type': 'string',
            'readonly': True,
            'label': 'Api Key',
            'description': 'This is top-secret! Don\'t share this!',
        }
    }
}]
