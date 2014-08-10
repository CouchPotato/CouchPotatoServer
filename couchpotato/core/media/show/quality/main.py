from couchpotato.core.event import addEvent
from couchpotato.core.media._base.quality.base import QualityBase

autoload = 'ShowQuality'


class ShowQuality(QualityBase):
    type = 'show'

    properties = {
        'codec': [
            {'identifier': 'mp2',     'label': 'MPEG-2/H.262',     'value': ['mpeg2']},
            {'identifier': 'mp4-asp', 'label': 'MPEG-4 ASP',       'value': ['divx', 'xvid']},
            {'identifier': 'mp4-avc', 'label': 'MPEG-4 AVC/H.264', 'value': ['avc', 'h264', 'x264']},
        ],
        'container': [
            {'identifier': 'avi',     'label': 'AVI',                 'ext': ['avi']},
            {'identifier': 'mov',     'label': 'QuickTime Movie',     'ext': ['mov']},
            {'identifier': 'mpeg-4',  'label': 'MPEG-4',              'ext': ['m4v', 'mp4']},
            {'identifier': 'mpeg-ts', 'label': 'MPEG-TS',             'ext': ['m2ts', 'ts']},
            {'identifier': 'mkv',     'label': 'Matroska',            'ext': ['mkv']},
            {'identifier': 'wmv',     'label': 'Windows Media Video', 'ext': ['wmv']}
        ],
        'resolution': [
            # TODO interlaced resolutions (auto-fill these options?)
            {'identifier':    'sd'},
            {'identifier':  '480p', 'width':  853, 'height':  480},
            {'identifier':  '576p', 'width': 1024, 'height':  576},
            {'identifier':  '720p', 'width': 1280, 'height':  720},
            {'identifier': '1080p', 'width': 1920, 'height': 1080}
        ],
        'source': [
            {'identifier': 'cam',      'label': 'Cam',      'value': ['camrip', 'hdcam']},
            {'identifier': 'hdtv',     'label': 'HDTV',     'value': ['hdtv']},
            {'identifier': 'screener', 'label': 'Screener', 'value': ['screener', 'dvdscr', 'ppvrip', 'dvdscreener', 'hdscr']},
            {'identifier': 'web',      'label': 'Web',      'value': ['webrip', ('web', 'rip'), 'webdl', ('web', 'dl')]}
        ]
    }

    qualities = [
        # TODO sizes will need to be adjusted for season packs

        # resolutions
        {'identifier': '1080p',    'label': '1080p',    'size': (800, 5000), 'codec': ['mp4-avc'], 'container': ['mpeg-ts', 'mkv'], 'resolution': ['1080p']},
        {'identifier': '720p',     'label': '720p',     'size': (800, 5000), 'codec': ['mp4-avc'], 'container': ['mpeg-ts', 'mkv'], 'resolution': ['720p']},

        # sources
        {'identifier': 'cam',      'label': 'Cam',      'size': (800, 5000), 'source': ['cam']},
        {'identifier': 'hdtv',     'label': 'HDTV',     'size': (800, 5000), 'source': ['hdtv']},
        {'identifier': 'screener', 'label': 'Screener', 'size': (800, 5000), 'source': ['screener']},
        {'identifier': 'web',      'label': 'Web',      'size': (800, 5000), 'source': ['web']},
    ]

    def __init__(self):
        super(ShowQuality, self).__init__()

        addEvent('quality.guess', self.guess)

    def guess(self, files, extra = None, size = None, types = None):
        if types and self.type not in types:
            return

        raise NotImplementedError()
