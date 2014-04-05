from .main import Downloader


def autoload():
    return Downloader()


config = [{
    'name': 'download_providers',
    'groups': [
        {
            'label': 'Downloaders',
            'description': 'You can select different downloaders for each type (usenet / torrent)',
            'type': 'list',
            'name': 'download_providers',
            'tab': 'downloaders',
            'options': [],
        },
    ],
}]
