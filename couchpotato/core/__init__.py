from uuid import uuid4

def start():
    pass

config = [{
    'name': 'core',
    'groups': [
        {
            'tab': 'general',
            'name': 'basics',
            'label': 'Basics',
            'description': 'Needs restart before changes take effect.',
            'options': [
                {
                    'name': 'username',
                    'default': '',
                    'type': 'string',
                    'label': 'Username',
                },
                {
                    'name': 'password',
                    'default': '',
                    'password': True,
                    'type': 'string',
                    'label': 'Password',
                },
                {
                    'name': 'host',
                    'advanced': True,
                    'default': '0.0.0.0',
                    'type': 'string',
                    'label': 'Host',
                    'description': 'Host that I should listen to. "0.0.0.0" listens to all ips.',
                },
                {
                    'name': 'port',
                    'default': 5000,
                    'type': 'int',
                    'label': 'Port',
                    'description': 'The port I should listen to.',
                },
                {
                    'name': 'launch_browser',
                    'default': True,
                    'type': 'bool',
                    'label': 'Launch Browser',
                    'description': 'Launch the browser when I start.',
                },
            ],
        },
        {
            'tab': 'general',
            'name': 'advanced',
            'label': 'Advanced',
            'description': "For those who know what the're doing",
            'advanced': True,
            'options': [
                {
                    'name': 'api_key',
                    'default': uuid4().hex,
                    'type': 'string',
                    'readonly': True,
                    'label': 'Api Key',
                    'description': "This is top-secret! Don't share this!",
                },
                {
                    'name': 'debug',
                    'default': False,
                    'type': 'bool',
                    'label': 'Debug',
                    'description': 'Enable debugging.',
                },
                {
                    'name': 'url_base',
                    'default': '',
                    'type': 'string',
                    'label': 'Url Base',
                    'description': 'When using mod_proxy use this to prepend the url with this.',
                },
            ],
        },
    ],
}]
