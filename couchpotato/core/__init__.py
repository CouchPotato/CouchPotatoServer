from uuid import uuid4

def start():
    pass

config = [{
    'name': 'core',
    'groups': [
        {
            'tab': 'general',
            'name': 'basics',
            'description': 'Needs restart before changes take effect.',
            'options': [
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
                {
                    'name': 'host',
                    'advanced': True,
                    'default': '0.0.0.0',
                    'label': 'IP',
                    'description': 'Host that I should listen to. "0.0.0.0" listens to all ips.',
                },
                {
                    'name': 'port',
                    'default': 5000,
                    'type': 'int',
                    'description': 'The port I should listen to.',
                },
                {
                    'name': 'launch_browser',
                    'default': 1,
                    'type': 'bool',
                    'label': 'Launch Browser',
                    'description': 'Launch the browser when I start.',
                },
            ],
        },
        {
            'tab': 'general',
            'name': 'advanced',
            'description': "For those who know what the're doing",
            'advanced': True,
            'options': [
                {
                    'name': 'api_key',
                    'default': uuid4().hex,
                    'readonly': 1,
                    'label': 'Api Key',
                    'description': "This is top-secret! Don't share this!",
                },
                {
                    'name': 'debug',
                    'default': 0,
                    'type': 'bool',
                    'label': 'Debug',
                    'description': 'Enable debugging.',
                },
                {
                    'name': 'url_base',
                    'default': '',
                    'label': 'Url Base',
                    'description': 'When using mod_proxy use this to append the url with this.',
                },
            ],
        },
    ],
}]
