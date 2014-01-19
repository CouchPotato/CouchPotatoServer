from .main import Core
from uuid import uuid4


def start():
    return Core()

config = [{
    'name': 'core',
    'order': 1,
    'groups': [
        {
            'tab': 'general',
            'name': 'basics',
            'description': 'Needs restart before changes take effect.',
            'wizard': True,
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
                    'name': 'port',
                    'default': 5050,
                    'type': 'int',
                    'description': 'The port I should listen to.',
                },
                {
                    'name': 'ssl_cert',
                    'description': 'Path to SSL server.crt',
                    'advanced': True,
                },
                {
                    'name': 'ssl_key',
                    'description': 'Path to SSL server.key',
                    'advanced': True,
                },
                {
                    'name': 'launch_browser',
                    'default': True,
                    'type': 'bool',
                    'description': 'Launch the browser when I start.',
                    'wizard': True,
                },
            ],
        },
        {
            'tab': 'general',
            'name': 'advanced',
            'description': "For those who know what they're doing",
            'advanced': True,
            'options': [
                {
                    'name': 'api_key',
                    'default': uuid4().hex,
                    'readonly': 1,
                    'description': 'Let 3rd party app do stuff. <a target="_self" href="../../docs/">Docs</a>',
                },
                {
                    'name': 'debug',
                    'default': 0,
                    'type': 'bool',
                    'description': 'Enable debugging.',
                },
                {
                    'name': 'development',
                    'default': 0,
                    'type': 'bool',
                    'description': 'Enable this if you\'re developing, and NOT in any other case, thanks.',
                },
                {
                    'name': 'data_dir',
                    'type': 'directory',
                    'description': 'Where cache/logs/etc are stored. Keep empty for defaults.',
                },
                {
                    'name': 'url_base',
                    'default': '',
                    'description': 'When using mod_proxy use this to append the url with this.',
                },
                {
                    'name': 'permission_folder',
                    'default': '0755',
                    'label': 'Folder CHMOD',
                    'description': 'Can be either decimal (493) or octal (leading zero: 0755)',
                },
                {
                    'name': 'permission_file',
                    'default': '0755',
                    'label': 'File CHMOD',
                    'description': 'Same as Folder CHMOD but for files',
                },
            ],
        },
    ],
}]
