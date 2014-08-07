from couchpotato.core.media._base.quality.base import QualityBase

autoload = 'MovieQuality'


class MovieQuality(QualityBase):
    qualities = [
        {'identifier': 'bd50', 'hd': True, 'allow_3d': True, 'size': (20000, 60000), 'label': 'BR-Disk', 'alternative': ['bd25', ('br', 'disk')], 'allow': ['1080p'], 'ext':['iso', 'img'], 'tags': ['bdmv', 'certificate', ('complete', 'bluray'), 'avc', 'mvc']},
        {'identifier': '1080p', 'hd': True, 'allow_3d': True, 'size': (4000, 20000), 'label': '1080p', 'width': 1920, 'height': 1080, 'alternative': [], 'allow': [], 'ext':['mkv', 'm2ts', 'ts'], 'tags': ['m2ts', 'x264', 'h264']},
        {'identifier': '720p', 'hd': True, 'allow_3d': True, 'size': (3000, 10000), 'label': '720p', 'width': 1280, 'height': 720, 'alternative': [], 'allow': [], 'ext':['mkv', 'ts'], 'tags': ['x264', 'h264']},
        {'identifier': 'brrip', 'hd': True, 'allow_3d': True, 'size': (700, 7000), 'label': 'BR-Rip', 'alternative': ['bdrip', ('br', 'rip')], 'allow': ['720p', '1080p'], 'ext':['mp4', 'avi'], 'tags': ['hdtv', 'hdrip', 'webdl', ('web', 'dl')]},
        {'identifier': 'dvdr', 'size': (3000, 10000), 'label': 'DVD-R', 'alternative': ['br2dvd', ('dvd', 'r')], 'allow': [], 'ext':['iso', 'img', 'vob'], 'tags': ['pal', 'ntsc', 'video_ts', 'audio_ts', ('dvd', 'r'), 'dvd9']},
        {'identifier': 'dvdrip', 'size': (600, 2400), 'label': 'DVD-Rip', 'width': 720, 'alternative': [('dvd', 'rip')], 'allow': [], 'ext':['avi'], 'tags': [('dvd', 'rip'), ('dvd', 'xvid'), ('dvd', 'divx')]},
        {'identifier': 'scr', 'size': (600, 1600), 'label': 'Screener', 'alternative': ['screener', 'dvdscr', 'ppvrip', 'dvdscreener', 'hdscr'], 'allow': ['dvdr', 'dvdrip', '720p', '1080p'], 'ext':[], 'tags': ['webrip', ('web', 'rip')]},
        {'identifier': 'r5', 'size': (600, 1000), 'label': 'R5', 'alternative': ['r6'], 'allow': ['dvdr', '720p'], 'ext':[]},
        {'identifier': 'tc', 'size': (600, 1000), 'label': 'TeleCine', 'alternative': ['telecine'], 'allow': ['720p'], 'ext':[]},
        {'identifier': 'ts', 'size': (600, 1000), 'label': 'TeleSync', 'alternative': ['telesync', 'hdts'], 'allow': ['720p'], 'ext':[]},
        {'identifier': 'cam', 'size': (600, 1000), 'label': 'Cam', 'alternative': ['camrip', 'hdcam'], 'allow': ['720p'], 'ext':[]},
    ]
