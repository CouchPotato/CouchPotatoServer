from couchpotato.core.event import addEvent
from couchpotato.core.media._base.quality.base import QualityBase

autoload = 'ShowQuality'


class ShowQuality(QualityBase):
    type = 'show'

    qualities = [
        # BluRay
        {'identifier': 'bluray_1080p', 'hd': True, 'size': (800, 5000), 'label': 'BluRay - 1080p', 'width': 1920, 'height': 1080, 'alternative': [], 'allow': [], 'ext':['mkv']},
        {'identifier': 'bluray_720p', 'hd': True, 'size': (800, 5000), 'label': 'BluRay - 720p', 'width': 1280, 'height': 720, 'alternative': [], 'allow': [], 'ext':['mkv']},
        # BDRip
        {'identifier': 'bdrip_1080p', 'hd': True, 'size': (800, 5000), 'label': 'BDRip - 1080p', 'width': 1920, 'height': 1080, 'alternative': [], 'allow': [], 'ext':['mkv']},
        {'identifier': 'bdrip_720p', 'hd': True, 'size': (800, 5000), 'label': 'BDRip - 720p', 'width': 1280, 'height': 720, 'alternative': [], 'allow': [], 'ext':['mkv']},
        # BRRip
        {'identifier': 'brrip_1080p', 'hd': True, 'size': (800, 5000), 'label': 'BRRip - 1080p', 'width': 1920, 'height': 1080, 'alternative': [], 'allow': [], 'ext':['mkv']},
        {'identifier': 'brrip_720p', 'hd': True, 'size': (800, 5000), 'label': 'BRRip - 720p', 'width': 1280, 'height': 720, 'alternative': [], 'allow': [], 'ext':['mkv']},
        # WEB-DL
        {'identifier': 'webdl_1080p', 'hd': True, 'size': (800, 5000), 'label': 'WEB-DL - 1080p', 'width': 1920, 'height': 1080, 'alternative': [], 'allow': [], 'ext':['mkv']},
        {'identifier': 'webdl_720p', 'hd': True, 'size': (800, 5000), 'label': 'WEB-DL - 720p', 'width': 1280, 'height': 720, 'alternative': [], 'allow': [], 'ext':['mkv']},
        {'identifier': 'webdl_480p', 'hd': True, 'size': (100, 5000), 'label': 'WEB-DL - 480p', 'width': 720, 'alternative': [], 'allow': [], 'ext':['mkv']},
        # HDTV
        {'identifier': 'hdtv_720p', 'hd': True, 'size': (800, 5000), 'label': 'HDTV - 720p', 'width': 1280, 'height': 720, 'alternative': [], 'allow': [], 'ext':['mkv']},
        {'identifier': 'hdtv_sd', 'hd': False, 'size': (100, 1000), 'label': 'HDTV - SD', 'width': 720, 'alternative': [], 'allow': [], 'ext':['mkv', 'mp4', 'avi']},
    ]

    def __init__(self):
        super(ShowQuality, self).__init__()

        addEvent('quality.guess', self.guess)

    def guess(self, files, extra = None, size = None, types = None):
        if types and self.type not in types:
            return

        raise NotImplementedError()
