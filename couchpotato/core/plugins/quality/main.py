from math import fabs, ceil
import traceback
import re

from CodernityDB.database import RecordNotFound
from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode, ss
from couchpotato.core.helpers.variable import mergeDicts, getExt, tryInt, splitString, tryFloat
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.plugins.quality.index import QualityIndex


log = CPLog(__name__)


class QualityPlugin(Plugin):

    _database = {
        'quality': QualityIndex
    }

    qualities = [
		{'identifier': '2160p', 'hd': True, 'allow_3d': True, 'size': (10000, 650000), 'median_size': 20000, 'label': '2160p', 'width': 3840, 'height': 2160, 'alternative': [], 'allow': [], 'ext':['mkv'], 'tags': ['x264', 'h264', '2160']},
        {'identifier': 'bd50', 'hd': True, 'allow_3d': True, 'size': (20000, 60000), 'median_size': 40000, 'label': 'BR-Disk', 'alternative': ['bd25', ('br', 'disk')], 'allow': ['1080p'], 'ext':['iso', 'img'], 'tags': ['bdmv', 'certificate', ('complete', 'bluray'), 'avc', 'mvc']},
        {'identifier': '1080p', 'hd': True, 'allow_3d': True, 'size': (4000, 20000), 'median_size': 10000, 'label': '1080p', 'width': 1920, 'height': 1080, 'alternative': [], 'allow': [], 'ext':['mkv', 'm2ts', 'ts'], 'tags': ['m2ts', 'x264', 'h264', '1080']},
        {'identifier': '720p', 'hd': True, 'allow_3d': True, 'size': (3000, 10000), 'median_size': 5500, 'label': '720p', 'width': 1280, 'height': 720, 'alternative': [], 'allow': [], 'ext':['mkv', 'ts'], 'tags': ['x264', 'h264', '720']},
        {'identifier': 'brrip', 'hd': True, 'allow_3d': True, 'size': (700, 7000), 'median_size': 2000, 'label': 'BR-Rip', 'alternative': ['bdrip', ('br', 'rip'), 'hdtv', 'hdrip'], 'allow': ['720p', '1080p', '2160p'], 'ext':['mp4', 'avi'], 'tags': ['webdl', ('web', 'dl')]},
        {'identifier': 'dvdr', 'size': (3000, 10000), 'median_size': 4500, 'label': 'DVD-R', 'alternative': ['br2dvd', ('dvd', 'r')], 'allow': [], 'ext':['iso', 'img', 'vob'], 'tags': ['pal', 'ntsc', 'video_ts', 'audio_ts', ('dvd', 'r'), 'dvd9']},
        {'identifier': 'dvdrip', 'size': (600, 2400), 'median_size': 1500, 'label': 'DVD-Rip', 'width': 720, 'alternative': [('dvd', 'rip')], 'allow': [], 'ext':['avi'], 'tags': [('dvd', 'rip'), ('dvd', 'xvid'), ('dvd', 'divx')]},
        {'identifier': 'scr', 'size': (600, 1600), 'median_size': 700, 'label': 'Screener', 'alternative': ['screener', 'dvdscr', 'ppvrip', 'dvdscreener', 'hdscr', 'webrip', ('web', 'rip')], 'allow': ['dvdr', 'dvdrip', '720p', '1080p'], 'ext':[], 'tags': []},
        {'identifier': 'r5', 'size': (600, 1000), 'median_size': 700, 'label': 'R5', 'alternative': ['r6'], 'allow': ['dvdr', '720p', '1080p'], 'ext':[]},
        {'identifier': 'tc', 'size': (600, 1000), 'median_size': 700, 'label': 'TeleCine', 'alternative': ['telecine'], 'allow': ['720p', '1080p'], 'ext':[]},
        {'identifier': 'ts', 'size': (600, 1000), 'median_size': 700, 'label': 'TeleSync', 'alternative': ['telesync', 'hdts'], 'allow': ['720p', '1080p'], 'ext':[]},
        {'identifier': 'cam', 'size': (600, 1000), 'median_size': 700, 'label': 'Cam', 'alternative': ['camrip', 'hdcam'], 'allow': ['720p', '1080p'], 'ext':[]}
    ]
    pre_releases = ['cam', 'ts', 'tc', 'r5', 'scr']
    threed_tags = {
        'sbs': [('half', 'sbs'), 'hsbs', ('full', 'sbs'), 'fsbs'],
        'ou': [('half', 'ou'), 'hou', ('full', 'ou'), 'fou'],
        '3d': ['2d3d', '3d2d', '3d'],
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
        addEvent('quality.fill', self.fill)

        addApiView('quality.size.save', self.saveSize)
        addApiView('quality.list', self.allView, docs = {
            'desc': 'List all available qualities',
            'return': {'type': 'object', 'example': """{
            'success': True,
            'list': array, qualities
}"""}
        })

        addEvent('app.initialize', self.fill, priority = 10)
        addEvent('app.load', self.fillBlank, priority = 120)

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

        temp = []
        for quality in self.qualities:
            quality_doc = db.get('quality', quality.get('identifier'), with_doc = True)['doc']
            q = mergeDicts(quality, quality_doc)
            temp.append(q)

        if len(temp) == len(self.qualities):
            self.cached_qualities = temp

        return temp

    def single(self, identifier = ''):

        db = get_db()
        quality_dict = {}

        try:
            quality = db.get('quality', identifier, with_doc = True)['doc']
        except RecordNotFound:
            log.error("Unable to find '%s' in the quality DB", indentifier)
            quality = None

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

    def fillBlank(self):
        db = get_db()

        try:
            existing = list(db.all('quality'))
            if len(self.qualities) > len(existing):
                log.error('Filling in new qualities')
                self.fill(reorder = True)
        except:
            log.error('Failed filling quality database with new qualities: %s', traceback.format_exc())

    def fill(self, reorder = False):

        try:
            db = get_db()

            order = 0
            for q in self.qualities:

                existing = None
                try:
                    existing = db.get('quality', q.get('identifier'), with_doc = reorder)
                except RecordNotFound:
                    pass

                if not existing:
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
                elif reorder:
                    log.info2('Updating quality order')
                    existing['doc']['order'] = order
                    db.update(existing['doc'])

                order += 1

            return True
        except:
            log.error('Failed: %s', traceback.format_exc())

        return False

    def guess(self, files, extra = None, size = None, use_cache = True):
        if not extra: extra = {}

        # Create hash for cache
        cache_key = str([f.replace('.' + getExt(f), '') if len(getExt(f)) < 4 else f for f in files])
        if use_cache:
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

        # Use metadata titles as extra check
        if extra and extra.get('titles'):
            files.extend(extra.get('titles'))

        for cur_file in files:
            words = re.split('\W+', cur_file.lower())
            name_year = fireEvent('scanner.name_year', cur_file, file_name = cur_file, single = True)
            threed_words = words
            if name_year and name_year.get('name'):
                split_name = splitString(name_year.get('name'), ' ')
                threed_words = [x for x in words if x not in split_name]

            for quality in qualities:
                contains_score = self.containsTagScore(quality, words, cur_file)
                threedscore = self.contains3D(quality, threed_words, cur_file) if quality.get('allow_3d') else (0, None)

                self.calcScore(score, quality, contains_score, threedscore, penalty = contains_score)

        size_scores = []
        for quality in qualities:

            # Evaluate score based on size
            size_score = self.guessSizeScore(quality, size = size)
            loose_score = self.guessLooseScore(quality, extra = extra)

            if size_score > 0:
                size_scores.append(quality)

            self.calcScore(score, quality, size_score + loose_score)

        # Add additional size score if only 1 size validated
        if len(size_scores) == 1:
            self.calcScore(score, size_scores[0], 7)
        del size_scores

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
        score = 0.0

        extension = words[-1]
        words = words[:-1]

        points = {
            'identifier': 25,
            'label': 25,
            'alternative': 20,
            'tags': 11,
            'ext': 5,
        }

        scored_on = []

        # Check alt and tags
        for tag_type in ['identifier', 'alternative', 'tags', 'label']:
            qualities = quality.get(tag_type, [])
            qualities = [qualities] if isinstance(qualities, (str, unicode)) else qualities

            for alt in qualities:
                if isinstance(alt, tuple):
                    if len(set(words) & set(alt)) == len(alt):
                        log.debug('Found %s via %s %s in %s', (quality['identifier'], tag_type, quality.get(tag_type), cur_file))
                        score += points.get(tag_type)

                if isinstance(alt, (str, unicode)) and ss(alt.lower()) in words and ss(alt.lower()) not in scored_on:
                    log.debug('Found %s via %s %s in %s', (quality['identifier'], tag_type, quality.get(tag_type), cur_file))
                    score += points.get(tag_type)

                    # Don't score twice on same tag
                    scored_on.append(ss(alt).lower())

        # Check extension
        for ext in quality.get('ext', []):
            if ext == extension:
                log.debug('Found %s with .%s extension in %s', (quality['identifier'], ext, cur_file))
                score += points['ext']

        return score

    def contains3D(self, quality, words, cur_file = ''):
        cur_file = ss(cur_file)

        for key in self.threed_tags:
            tags = self.threed_tags.get(key, [])

            for tag in tags:
                if isinstance(tag, tuple):
                    if len(set(words) & set(tag)) == len(tag):
                        log.debug('Found %s in %s', (tag, cur_file))
                        return 1, key
                elif tag in words:
                    log.debug('Found %s in %s', (tag, cur_file))
                    return 1, key

        return 0, None

    def guessLooseScore(self, quality, extra = None):

        score = 0

        if extra:

            # Check width resolution, range 20
            if quality.get('width') and (quality.get('width') - 20) <= extra.get('resolution_width', 0) <= (quality.get('width') + 20):
                log.debug('Found %s via resolution_width: %s == %s', (quality['identifier'], quality.get('width'), extra.get('resolution_width', 0)))
                score += 10

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

            size = tryFloat(size)
            size_min = tryFloat(quality['size_min'])
            size_max = tryFloat(quality['size_max'])

            if size_min <= size <= size_max:
                log.debug('Found %s via release size: %s MB < %s MB < %s MB', (quality['identifier'], size_min, size, size_max))

                proc_range = size_max - size_min
                size_diff = size - size_min
                size_proc = (size_diff / proc_range)

                median_diff = quality['median_size'] - size_min
                median_proc = (median_diff / proc_range)

                max_points = 8
                score += ceil(max_points - (fabs(size_proc - median_proc) * max_points))
            else:
                score -= 5

        return score

    def calcScore(self, score, quality, add_score, threedscore = (0, None), penalty = 0):

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
                score[allow]['score'] -= ((penalty * 2) if self.cached_order[allow] < self.cached_order[quality['identifier']] else penalty) * 2

            # Give panelty for all other qualities
            for q in self.qualities:
                if quality.get('identifier') != q.get('identifier') and score.get(q.get('identifier')):
                    score[q.get('identifier')]['score'] -= 1

    def isFinish(self, quality, profile, release_age = 0):
        if not isinstance(profile, dict) or not profile.get('qualities'):
            # No profile so anything (scanned) is good enough
            return True

        try:
            index = [i for i, identifier in enumerate(profile['qualities']) if identifier == quality['identifier'] and bool(profile['3d'][i] if profile.get('3d') else False) == bool(quality.get('is_3d', False))][0]

            if index == 0 or (profile['finish'][index] and int(release_age) >= int(profile.get('stop_after', [0])[0])):
                return True

            return False
        except:
            return False

    def isHigher(self, quality, compare_with, profile = None):
        if not isinstance(profile, dict) or not profile.get('qualities'):
            profile = fireEvent('profile.default', single = True)

        # Try to find quality in profile, if not found: a quality we do not want is lower than anything else
        try:
            quality_order = [i for i, identifier in enumerate(profile['qualities']) if identifier == quality['identifier'] and bool(profile['3d'][i] if profile.get('3d') else 0) == bool(quality.get('is_3d', 0))][0]
        except:
            log.debug('Quality %s not found in profile identifiers %s', (quality['identifier'] + (' 3D' if quality.get('is_3d', 0) else ''), \
                [identifier + (' 3D' if (profile['3d'][i] if profile.get('3d') else 0) else '') for i, identifier in enumerate(profile['qualities'])]))
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
            'The.Movie.2014.3D.1080p.BluRay.AVC.DTS-HD.MA.5.1-GroupName': {'size': 30000, 'quality': 'bd50', 'is_3d': True},
            '/home/namehou/Movie Monuments (2012)/Movie Monuments.mkv': {'size': 5500, 'quality': '720p', 'is_3d': False},
            '/home/namehou/Movie Monuments (2012)/Movie Monuments Full-OU.mkv': {'size': 5500, 'quality': '720p', 'is_3d': True},
            '/home/namehou/Movie Monuments (2013)/Movie Monuments.mkv': {'size': 10000, 'quality': '1080p', 'is_3d': False},
            '/home/namehou/Movie Monuments (2013)/Movie Monuments Full-OU.mkv': {'size': 10000, 'quality': '1080p', 'is_3d': True},
            '/volume1/Public/3D/Moviename/Moviename (2009).3D.SBS.ts': {'size': 7500, 'quality': '1080p', 'is_3d': True},
            '/volume1/Public/Moviename/Moviename (2009).ts': {'size': 7500, 'quality': '1080p'},
            '/movies/BluRay HDDVD H.264 MKV 720p EngSub/QuiQui le fou (criterion collection #123, 1915)/QuiQui le fou (1915) 720p x264 BluRay.mkv': {'size': 5500, 'quality': '720p'},
            'C:\\movies\QuiQui le fou (collection #123, 1915)\QuiQui le fou (1915) 720p x264 BluRay.mkv': {'size': 5500, 'quality': '720p'},
            'C:\\movies\QuiQui le fou (collection #123, 1915)\QuiQui le fou (1915) half-sbs 720p x264 BluRay.mkv': {'size': 5500, 'quality': '720p', 'is_3d': True},
            'Moviename 2014 720p HDCAM XviD DualAudio': {'size': 4000, 'quality': 'cam'},
            'Moviename (2014) - 720p CAM x264': {'size': 2250, 'quality': 'cam'},
            'Movie Name (2014).mp4': {'size': 750, 'quality': 'brrip'},
            'Moviename.2014.720p.R6.WEB-DL.x264.AC3-xyz': {'size': 750, 'quality': 'r5'},
            'Movie name 2014 New Source 720p HDCAM x264 AC3 xyz': {'size': 750, 'quality': 'cam'},
            'Movie.Name.2014.720p.HD.TS.AC3.x264': {'size': 750, 'quality': 'ts'},
            'Movie.Name.2014.1080p.HDrip.x264.aac-ReleaseGroup': {'size': 7000, 'quality': 'brrip'},
            'Movie.Name.2014.HDCam.Chinese.Subs-ReleaseGroup': {'size': 15000, 'quality': 'cam'},
            'Movie Name 2014 HQ DVDRip X264 AC3 (bla)': {'size': 0, 'quality': 'dvdrip'},
            'Movie Name1 (2012).mkv': {'size': 4500, 'quality': '720p'},
            'Movie Name (2013).mkv': {'size': 8500, 'quality': '1080p'},
            'Movie Name (2014).mkv': {'size': 4500, 'quality': '720p', 'extra': {'titles': ['Movie Name 2014 720p Bluray']}},
            'Movie Name (2015).mkv': {'size': 500, 'quality': '1080p', 'extra': {'resolution_width': 1920}},
            'Movie Name (2015).mp4': {'size': 6500, 'quality': 'brrip'},
            'Movie Name.2014.720p Web-Dl Aac2.0 h264-ReleaseGroup': {'size': 3800, 'quality': 'brrip'},
            'Movie Name.2014.720p.WEBRip.x264.AC3-ReleaseGroup': {'size': 3000, 'quality': 'scr'},
            'Movie.Name.2014.1080p.HDCAM.-.ReleaseGroup': {'size': 5300, 'quality': 'cam'},
            'Movie.Name.2014.720p.HDSCR.4PARTS.MP4.AAC.ReleaseGroup': {'size': 2401, 'quality': 'scr'},
            'Movie.Name.2014.720p.BluRay.x264-ReleaseGroup': {'size': 10300, 'quality': '720p'},
            'Movie.Name.2014.720.Bluray.x264.DTS-ReleaseGroup': {'size': 9700, 'quality': '720p'},
            'Movie Name 2015 2160p SourceSite WEBRip DD5 1 x264-ReleaseGroup': {'size': 21800, 'quality': '2160p'},
            'Movie Name 2012 2160p WEB-DL FLAC 5 1 x264-ReleaseGroup': {'size': 59650, 'quality': '2160p'}
        }

        correct = 0
        for name in tests:
            test_quality = self.guess(files = [name], extra = tests[name].get('extra', None), size = tests[name].get('size', None), use_cache = False) or {}
            success = test_quality.get('identifier') == tests[name]['quality'] and test_quality.get('is_3d') == tests[name].get('is_3d', False)
            if not success:
                log.error('%s failed check, thinks it\'s "%s" expecting "%s"', (name,
                                                                            test_quality.get('identifier') + (' 3D' if test_quality.get('is_3d') else ''),
                                                                            tests[name]['quality'] + (' 3D' if tests[name].get('is_3d') else '')
                ))

            correct += success

        if correct == len(tests):
            log.info('Quality test successful')
            return True
        else:
            log.error('Quality test failed: %s out of %s succeeded', (correct, len(tests)))


