from .main import Nzbs

def start():
    return Nzbs()

config = [{
    'name': 'nzbs',
    'groups': [
        {
            'tab': 'providers',
            'name': 'nzbs',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'id',
                    'label': 'Id',
                    'description': 'Can be found <a href="http://nzbs.org/index.php?action=rss" target="_blank">here</a>, the number after "&amp;i="',
                },
                {
                    'name': 'api_key',
                    'label': 'Api Key',
                    'description': 'Can be found <a href="http://nzbs.org/index.php?action=rss" target="_blank">here</a>, the string after "&amp;h="'
                },
            ],
        },
    ],
}]
