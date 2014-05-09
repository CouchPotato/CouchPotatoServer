import traceback
import re

from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode, ss
from couchpotato.core.helpers.variable import mergeDicts, getExt, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.plugins.quality.index import QualityIndex


log = CPLog(__name__)


class QualityPlugin(Plugin):

    _database = {
        'quality': QualityIndex
    }

    qualities = [
        {'identifier': 'bd50', 'hd': True, 'allow_3d': True, 'size': (20000, 60000), 'label': 'BR-Disk', 'alternative': ['bd25'], 'allow': ['1080p'], 'ext':['iso', 'img'], 'tags': ['bdmv', 'certificate', ('complete', 'bluray'), 'avc', 'mvc']},
        {'identifier': '1080p', 'hd': True, 'allow_3d': True, 'size': (4000, 20000), 'label': '1080p', 'width': 1920, 'height': 1080, 'alternative': [], 'allow': [], 'ext':['mkv', 'm2ts'], 'tags': ['m2ts', 'x264', 'h264']},
        {'identifier': '720p', 'hd': True, 'allow_3d': True, 'size': (3000, 10000), 'label': '720p', 'width': 1280, 'height': 720, 'alternative': [], 'allow': [], 'ext':['mkv', 'ts'], 'tags': ['x264', 'h264']},
        {'identifier': 'brrip', 'hd': True, 'allow_3d': True, 'size': (700, 7000), 'label': 'BR-Rip', 'alternative': ['bdrip'], 'allow': ['720p', '1080p'], 'ext':[], 'tags': ['hdtv', 'hdrip', 'webdl', ('web', 'dl')]},
        {'identifier': 'dvdr', 'size': (3000, 10000), 'label': 'DVD-R', 'alternative': ['br2dvd'], 'allow': [], 'ext':['iso', 'img', 'vob'], 'tags': ['pal', 'ntsc', 'video_ts', 'audio_ts', ('dvd', 'r'), 'dvd9']},
        {'identifier': 'dvdrip', 'size': (600, 2400), 'label': 'DVD-Rip', 'width': 720, 'alternative': [], 'allow': [], 'ext':[], 'tags': [('dvd', 'rip'), ('dvd', 'xvid'), ('dvd', 'divx')]},
        {'identifier': 'scr', 'size': (600, 1600), 'label': 'Screener', 'alternative': ['screener', 'dvdscr', 'ppvrip', 'dvdscreener', 'hdscr'], 'allow': ['dvdr', 'dvdrip', '720p', '1080p'], 'ext':[], 'tags': ['webrip', ('web', 'rip')]},
        {'identifier': 'r5', 'size': (600, 1000), 'label': 'R5', 'alternative': ['r6'], 'allow': ['dvdr'], 'ext':[]},
        {'identifier': 'tc', 'size': (600, 1000), 'label': 'TeleCine', 'alternative': ['telecine'], 'allow': [], 'ext':[]},
        {'identifier': 'ts', 'size': (600, 1000), 'label': 'TeleSync', 'alternative': ['telesync', 'hdts'], 'allow': [], 'ext':[]},
        {'identifier': 'cam', 'size': (600, 1000), 'label': 'Cam', 'alternative': ['camrip', 'hdcam'], 'allow': [], 'ext':[]}
    ]
    pre_releases = ['cam', 'ts', 'tc', 'r5', 'scr']
    threed_tags = {
        'sbs': [('half', 'sbs'), 'hsbs', ('full', 'sbs'), 'fsbs'],
        'ou': [('half', 'ou'), 'hou', ('full', 'ou'), 'fou'],
        '3d': ['2d3d', '3d2d'],
    }

    cached_qualities = None
    cached_order = None

    def __init__(self):
        addEvent('quality.all', self.all)
        addEvent('quality.single', self.single)
        addEvent('quality.guess', self.guess)
        addEvent('quality.pre_releases', self.preReleases)
        addEvent('quality.order', self.getOrder)
        addEvent('quality.ishigher', self.isHigher)
        addEvent('quality.isfinish', self.isFinish)

        addApiView('quality.size.save', self.saveSize)
        addApiView('quality.list', self.allView, docs = {
            'desc': 'List all available qualities',
            'return': {'type': 'object', 'example': """{
            'success': True,
            'list': array, qualities
}"""}
        })

        addEvent('app.initialize', self.fill, priority = 10)

        addEvent('app.test', self.doTest)

        self.order = []
        self.addOrder()

    def addOrder(self):
        self.order = []
        for q in self.qualities:
            self.order.append(q.get('identifier'))

    def getOrder(self):
        return self.order

    def preReleases(self):
        return self.pre_releases

    def allView(self, **kwargs):

        return {
            'success': True,
            'list': self.all()
        }

    def all(self):

        if self.cached_qualities:
            return self.cached_qualities

        db = get_db()

        qualities = db.all('quality', with_doc = True)

        temp = []
        for quality in qualities:
            quality = quality['doc']
            q = mergeDicts(self.getQuality(quality.get('identifier')), quality)
            temp.append(q)

        self.cached_qualities = temp

        return temp

    def single(self, identifier = ''):

        db = get_db()
        quality_dict = {}

        quality = db.get('quality', identifier, with_doc = True)['doc']
        if quality:
            quality_dict = mergeDicts(self.getQuality(quality['identifier']), quality)

        return quality_dict

    def getQuality(self, identifier):

        for q in self.qualities:
            if identifier == q.get('identifier'):
                return q

    def saveSize(self, **kwargs):

        try:
            db = get_db()
            quality = db.get('quality', kwargs.get('identifier'), with_doc = True)

            if quality:
                quality['doc'][kwargs.get('value_type')] = tryInt(kwargs.get('value'))
                db.update(quality['doc'])

            self.cached_qualities = None

            return {
                'success': True
            }
        except:
            log.error('Failed: %s', traceback.format_exc())

        return {
            'success': False
        }

    def fill(self):

        try:
            db = get_db()

            order = 0
            for q in self.qualities:

                db.insert({
                    '_t': 'quality',
                    'order': order,
                    'identifier': q.get('identifier'),
                    'size_min': tryInt(q.get('size')[0]),
                    'size_max': tryInt(q.get('size')[1]),
                })

                log.info('Creating profile: %s', q.get('label'))
                db.insert({
                    '_t': 'profile',
                    'order': order + 20,  # Make sure it goes behind other profiles
                    'core': True,
                    'qualities': [q.get('identifier')],
                    'label': toUnicode(q.get('label')),
                    'finish': [True],
                    'wait_for': [0],
                })

                order += 1

            return True
        except:
            log.error('Failed: %s', traceback.format_exc())

        return False

    def guess(self, files, extra = None, size = None):
        if not extra: extra = {}

        # Create hash for cache
        cache_key = str([f.replace('.' + getExt(f), '') if len(getExt(f)) < 4 else f for f in files])
        cached = self.getCache(cache_key)
        if cached and len(extra) == 0:
            return cached

        qualities = self.all()

        # Start with 0
        score = {}
        for quality in qualities:
            score[quality.get('identifier')] = {
                'score': 0,
                '3d': {}
            }

        for cur_file in files:
            words = re.split('\W+', cur_file.lower())

            for quality in qualities:
                contains_score = self.containsTagScore(quality, words, cur_file)
                threedscore = self.contains3D(quality, words, cur_file) if quality.get('allow_3d') else (0, None)

                self.calcScore(score, quality, contains_score, threedscore)

        # Evaluate score based on size
        for quality in qualities:
            size_score = self.guessSizeScore(quality, size = size)
            self.calcScore(score, quality, size_score, penalty = False)

        # Try again with loose testing
        for quality in qualities:
            loose_score = self.guessLooseScore(quality, extra = extra)
            self.calcScore(score, quality, loose_score, penalty = False)

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

    def containsTagScore(self, quality, words, cur_file = ''):
        cur_file = ss(cur_file)
        score = 0

        points = {
            'identifier': 10,
            'label': 10,
            'alternative': 9,
            'tags': 9,
            'ext': 3,
        }

        # Check alt and tags
        for tag_type in ['identifier', 'alternative', 'tags', 'label']:
            qualities = quality.get(tag_type, [])
            qualities = [qualities] if isinstance(qualities, (str, unicode)) else qualities

            for alt in qualities:
                if isinstance(alt, tuple):
                    if len(set(words) & set(alt)) == len(alt):
                        log.debug('Found %s via %s %s in %s', (quality['identifier'], tag_type, quality.get(tag_type), cur_file))
                        score += points.get(tag_type)

                if isinstance(alt, (str, unicode)) and ss(alt.lower()) in cur_file.lower():
                    log.debug('Found %s via %s %s in %s', (quality['identifier'], tag_type, quality.get(tag_type), cur_file))
                    score += points.get(tag_type) / 2

            if list(set(qualities) & set(words)):
                log.debug('Found %s via %s %s in %s', (quality['identifier'], tag_type, quality.get(tag_type), cur_file))
                score += points.get(tag_type)

        # Check extention
        for ext in quality.get('ext', []):
            if ext == words[-1]:
                log.debug('Found %s extension in %s', (ext, cur_file))
                score += points['ext']

        return score

    def contains3D(self, quality, words, cur_file = ''):
        cur_file = ss(cur_file)

        for key in self.threed_tags:
            tags = self.threed_tags.get(key, [])

            for tag in tags:
                if (isinstance(tag, tuple) and '.'.join(tag) in '.'.join(words)) or (isinstance(tag, (str, unicode)) and ss(tag.lower()) in cur_file.lower()):
                    log.debug('Found %s in %s', (tag, cur_file))
                    return 1, key

            if list(set([key]) & set(words)):
                log.debug('Found %s in %s', (key, cur_file))
                return 1, key

        return 0, None

    def guessLooseScore(self, quality, extra = None):

        score = 0

        if extra:

            # Check width resolution, range 20
            if quality.get('width') and (quality.get('width') - 20) <= extra.get('resolution_width', 0) <= (quality.get('width') + 20):
                log.debug('Found %s via resolution_width: %s == %s', (quality['identifier'], quality.get('width'), extra.get('resolution_width', 0)))
                score += 5

            # Check height resolution, range 20
            if quality.get('height') and (quality.get('height') - 20) <= extra.get('resolution_height', 0) <= (quality.get('height') + 20):
                log.debug('Found %s via resolution_height: %s == %s', (quality['identifier'], quality.get('height'), extra.get('resolution_height', 0)))
                score += 5

            if quality.get('identifier') == 'dvdrip' and 480 <= extra.get('resolution_width', 0) <= 720:
                log.debug('Add point for correct dvdrip resolutions')
                score += 1

        return score


    def guessSizeScore(self, quality, size = None):

        score = 0

        if size:

            if tryInt(quality['size_min']) <= tryInt(size) <= tryInt(quality['size_max']):
                log.info2('Found %s via release size: %s MB < %s MB < %s MB', (quality['identifier'], quality['size_min'], size, quality['size_max']))
                score += 5

        return score

    def calcScore(self, score, quality, add_score, threedscore = (0, None), penalty = True):

        score[quality['identifier']]['score'] += add_score

        threedscore, threedtag = threedscore
        if threedscore and threedtag:
            if threedscore not in score[quality['identifier']]['3d']:
                score[quality['identifier']]['3d'][threedtag] = 0

            score[quality['identifier']]['3d'][threedtag] += threedscore

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
                score[q.get('identifier')]['score'] -= 1

    def isFinish(self, quality, profile):
        if not isinstance(profile, dict) or not profile.get('qualities'):
            return False

        try:
            quality_order = [i for i, identifier in enumerate(profile['qualities']) if identifier == quality['identifier'] and bool(profile['3d'][i] if profile.get('3d') else 0) == bool(quality.get('is_3d', 0))][0]
            return profile['finish'][quality_order]
        except:
            return False

    def isHigher(self, quality, compare_with, profile = None):
        if not isinstance(profile, dict) or not profile.get('qualities'):
            profile = {'qualities': self.order}

        # Try to find quality in profile, if not found: a quality we do not want is lower than anything else
        try:
            quality_order = [i for i, identifier in enumerate(profile['qualities']) if identifier == quality['identifier'] and bool(profile['3d'][i] if profile.get('3d') else 0) == bool(quality.get('is_3d', 0))][0]
        except:
            log.debug('Quality %s not found in profile identifiers %s', (quality['identifier'] + (' 3D' if quality.get('is_3d', 0) else ''), \
                [identifier + ('3D' if (profile['3d'][i] if profile.get('3d') else 0) else '') for i, identifier in enumerate(profile['qualities'])]))
            return 'lower'

        # Try to find compare quality in profile, if not found: anything is higher than a not wanted quality
        try:
            compare_order = [i for i, identifier in enumerate(profile['qualities']) if identifier == compare_with['identifier'] and bool(profile['3d'][i] if profile.get('3d') else 0) == bool(compare_with.get('is_3d', 0))][0]
        except:
            log.debug('Compare quality %s not found in profile identifiers %s', (compare_with['identifier'] + (' 3D' if compare_with.get('is_3d', 0) else ''), \
                [identifier + (' 3D' if (profile['3d'][i] if profile.get('3d') else 0) else '') for i, identifier in enumerate(profile['qualities'])]))
            return 'higher'

        # Note to self: a lower number means higher quality
        if quality_order > compare_order:
            return 'lower'
        elif quality_order == compare_order:
            return 'equal'
        else:
            return 'higher'

    def doTest(self):

        tests = {
            'Movie Name (1999)-DVD-Rip.avi': {'size': 700, 'quality': 'dvdrip'},
            'Movie Name 1999 720p Bluray.mkv': {'size': 4200, 'quality': '720p'},
            'Movie Name 1999 BR-Rip 720p.avi': {'size': 1000, 'quality': 'brrip'},
            'Movie Name 1999 720p Web Rip.avi': {'size': 1200, 'quality': 'scr'},
            'Movie Name 1999 Web DL.avi': {'size': 800, 'quality': 'brrip'},
            'Movie.Name.1999.1080p.WEBRip.H264-Group': {'size': 1500, 'quality': 'scr'},
            'Movie.Name.1999.DVDRip-Group': {'size': 750, 'quality': 'dvdrip'},
            'Movie.Name.1999.DVD-Rip-Group': {'size': 700, 'quality': 'dvdrip'},
            'Movie.Name.1999.DVD-R-Group': {'size': 4500, 'quality': 'dvdr'},
            'Movie.Name.Camelie.1999.720p.BluRay.x264-Group': {'size': 5500, 'quality': '720p'},
            'Movie.Name.2008.German.DL.AC3.1080p.BluRay.x264-Group': {'size': 8500, 'extra': {'resolution_width': 1920, 'resolution_height': 1080} , 'quality': '1080p'},
            'Movie.Name.2004.GERMAN.AC3D.DL.1080p.BluRay.x264-Group': {'size': 8000, 'quality': '1080p'},
            'Movie.Name.2013.BR-Disk-Group.iso': {'size': 48000, 'quality': 'bd50'},
            'Movie.Name.2013.2D+3D.BR-Disk-Group.iso': {'size': 52000, 'quality': 'bd50', 'is_3d': True},
            'Movie.Rising.Name.Girl.2011.NTSC.DVD9-GroupDVD': {'size': 7200, 'quality': 'dvdr'},
            'Movie Name (2013) 2D + 3D': {'size': 49000, 'quality': 'bd50', 'is_3d': True},
            'Movie Monuments 2013 BrRip 1080p': {'size': 1800, 'quality': 'brrip'},
            'Movie Monuments 2013 BrRip 720p': {'size': 1300, 'quality': 'brrip'},
        }

        correct = 0
        for name in tests:
            test_quality = self.guess(files = [name], extra = tests[name].get('extra', None), size = tests[name].get('size', None)) or {}
            success = test_quality.get('identifier') == tests[name]['quality'] and test_quality.get('is_3d') == tests[name].get('is_3d', False)
            if not success:
                log.error('%s failed check, thinks it\'s %s', (name, self.guess([name]).get('identifier')))

            correct += success

        if correct == len(tests):
            log.info('Quality test successful')
            return True
        else:
            log.error('Quality test failed: %s out of %s succeeded', (correct, len(tests)))


