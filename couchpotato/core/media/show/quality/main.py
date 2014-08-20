from caper import Caper

from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import getExt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.quality.base import QualityBase

log = CPLog(__name__)

autoload = 'ShowQuality'


class ShowQuality(QualityBase):
    type = 'show'

    properties = {
        'codec': [
            {'identifier': 'mp2',     'label': 'MPEG-2/H.262',     'value': ['mpeg2']},
            {'identifier': 'mp4-asp', 'label': 'MPEG-4 ASP',       'value': ['divx', 'xvid']},
            {'identifier': 'mp4-avc', 'label': 'MPEG-4 AVC/H.264', 'value': ['avc', 'h264', 'x264', ('h', '264')]},
        ],
        'container': [
            {'identifier': 'avi',     'label': 'AVI',                 'value': ['avi']},
            {'identifier': 'mov',     'label': 'QuickTime Movie',     'value': ['mov']},
            {'identifier': 'mpeg-4',  'label': 'MPEG-4',              'value': ['m4v', 'mp4']},
            {'identifier': 'mpeg-ts', 'label': 'MPEG-TS',             'value': ['m2ts', 'ts']},
            {'identifier': 'mkv',     'label': 'Matroska',            'value': ['mkv']},
            {'identifier': 'wmv',     'label': 'Windows Media Video', 'value': ['wmv']}
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
        {'identifier': '1080p',    'label': '1080p',    'size': (1000, 25000), 'codec': ['mp4-avc'], 'container': ['mpeg-ts', 'mkv'], 'resolution': ['1080p']},
        {'identifier': '720p',     'label': '720p',     'size': (1000, 5000), 'codec': ['mp4-avc'], 'container': ['mpeg-ts', 'mkv'], 'resolution': ['720p']},
        {'identifier': '480p',     'label': '480p',     'size': (800, 5000), 'codec': ['mp4-avc'], 'container': ['mpeg-ts', 'mkv'], 'resolution': ['480p']},

        # sources
        {'identifier': 'cam',      'label': 'Cam',      'size': (800, 5000), 'source': ['cam']},
        {'identifier': 'hdtv',     'label': 'HDTV',     'size': (800, 5000), 'source': ['hdtv']},
        {'identifier': 'screener', 'label': 'Screener', 'size': (800, 5000), 'source': ['screener']},
        {'identifier': 'web',      'label': 'Web',      'size': (800, 5000), 'source': ['web']},
    ]

    def __init__(self):
        super(ShowQuality, self).__init__()

        addEvent('quality.guess', self.guess)

        self.caper = Caper()

    def guess(self, files, extra = None, size = None, types = None):
        if types and self.type not in types:
            return

        log.debug('Trying to guess quality of: %s', files)

        if not extra: extra = {}

        # Create hash for cache
        cache_key = str([f.replace('.' + getExt(f), '') if len(getExt(f)) < 4 else f for f in files])
        cached = self.getCache(cache_key)
        if cached and len(extra) == 0:
            return cached

        qualities = self.all()

        # Score files against each quality
        score = self.score(files, qualities = qualities)

        if score is None:
            return None

        # Return nothing if all scores are <= 0
        has_non_zero = 0
        for s in score:
            if score[s]['score'] > 0:
                has_non_zero += 1

        if not has_non_zero:
            return None

        heighest_quality = max(score, key = lambda p: score[p]['score'])
        if heighest_quality:
            for quality in qualities:
                if quality.get('identifier') == heighest_quality:
                    quality['is_3d'] = False
                    if score[heighest_quality].get('3d'):
                        quality['is_3d'] = True
                    return self.setCache(cache_key, quality)

        return None

    def score(self, files, qualities = None, types = None):
        if types and self.type not in types:
            return None

        if not qualities:
            qualities = self.all()

        qualities_expanded = [self.expand(q.copy()) for q in qualities]

        # Start with 0
        score = {}
        for quality in qualities:
            score[quality.get('identifier')] = {
                'score': 0,
                '3d': {}
            }

        for cur_file in files:
            match = self.caper.parse(cur_file, 'scene')

            if len(match.chains) < 1:
                log.info2('Unable to parse "%s", ignoring file')
                continue

            chain = match.chains[0]

            for quality in qualities_expanded:
                property_score = self.propertyScore(quality, chain)

                self.calcScore(score, quality, property_score)

        return score

    def propertyScore(self, quality, chain):
        score = 0

        if 'video' not in chain.info:
            return 0

        info = fireEvent('matcher.flatten_info', chain.info['video'], single = True)

        for key in ['codec', 'resolution', 'source']:
            if key not in quality:
                # No specific property required
                score += 5
                continue

            available = list(self.getInfo(info, key))
            found = False

            for property in quality[key]:
                required = property['value'] if 'value' in property else [property['identifier']]

                if set(available) & set(required):
                    score += 10
                    found = True
                    break

            if not found:
                score -= 10

        return score

    def getInfo(self, info, key):
        for value in info.get(key, []):
            if isinstance(value, list):
                yield tuple([x.lower() for x in value])
            else:
                yield value.lower()

    def calcScore(self, score, quality, add_score, threedscore = (0, None), penalty = True):
        score[quality['identifier']]['score'] += add_score

        # Set order for allow calculation (and cache)
        if not self.cached_order:
            self.cached_order = {}
            for q in self.qualities:
                self.cached_order[q.get('identifier')] = self.qualities.index(q)

        if penalty and add_score != 0:
            for allow in quality.get('allow', []):
                score[allow]['score'] -= 40 if self.cached_order[allow] < self.cached_order[quality['identifier']] else 5

            # Give panelty for all lower qualities
            for q in self.qualities[self.order.index(quality.get('identifier'))+1:]:
                if score.get(q.get('identifier')):
                    score[q.get('identifier')]['score'] -= 1
