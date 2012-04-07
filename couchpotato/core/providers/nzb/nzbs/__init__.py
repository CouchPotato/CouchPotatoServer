from .main import Nzbs

def start():
    return Nzbs()

config = [{
    'name': 'nzbs',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': 'nzbs',
            'description': 'Id and Key can be found <a href="http://nzbs.org/index.php?action=rss" target="_blank">on your nzbs.org RSS page</a>.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'id',
                    'label': 'Id',
                    'description': 'The number after "&amp;i="',
                },
                {
                    'name': 'api_key',
                    'label': 'Api Key',
                    'description': 'The string after "&amp;h="'
                },
            ],
        },
    ],
}]
