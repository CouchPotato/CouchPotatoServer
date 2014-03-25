from .main import NZBto


def start():
    return NZBto()

config = [{
    'name': 'nzbto',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'nzb_providers',
            'name': 'NZBto',
            'description': 'German Provider. Account and Proxy requiered See <a href="http://nzb.to/">NZB.to</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'proxy',
                    'label': 'Proxy Server',
                    'description': 'URL for Proxy Server',
                },
                {
                    'name': 'nzbto_username',
                    'label': 'Username',
                    'description': 'nzb.to Username',
                },
                {
                    'name': 'nzbto_password',
                    'label': 'Password',
                    'description': 'nzb.to Password',
                }
            ],
        },
    ],
}]
