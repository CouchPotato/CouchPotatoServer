from .main import XBMC

def start():
    return XBMC()

config = [{
    'name': 'xbmc',
    'groups': [
        {
            'tab': 'renamer',
            'subtab': 'metadata',
            'name': 'xbmc_metadata',
            'label': 'XBMC',
            'description': 'Enable metadata XBMC can understand',
            'options': [
                {
                    'name': 'meta_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'meta_nfo',
                    'label': 'NFO',
                    'default': True,
                    'type': 'bool',
                },
                {
                    'name': 'meta_nfo_name',
                    'label': 'NFO filename',
                    'default': '%s.nfo',
                    'advanced': True,
                    'description': '<strong>%s</strong> is the rootname of the movie. For example "/path/to/movie cd1.mkv" will be "/path/to/movie"'
                },
                {
                    'name': 'meta_url_only',
                    'label': 'Only IMDB URL',
                    'default': False,
                    'advanced': True,
                    'description': 'Create a nfo with only the IMDB url inside',
                    'type': 'bool',
                },
                {
                    'name': 'meta_fanart',
                    'label': 'Fanart',
                    'default': True,
                    'type': 'bool',
                },
                {
                    'name': 'meta_fanart_name',
                    'label': 'Fanart filename',
                    'default': '%s-fanart.jpg',
                    'advanced': True,
                },
                {
                    'name': 'meta_thumbnail',
                    'label': 'Thumbnail',
                    'default': True,
                    'type': 'bool',
                },
                {
                    'name': 'meta_thumbnail_name',
                    'label': 'Thumbnail filename',
                    'default': '%s.tbn',
                    'advanced': True,
                },
            ],
        },
    ],
}]
