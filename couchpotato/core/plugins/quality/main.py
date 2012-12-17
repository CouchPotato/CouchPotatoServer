from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.request import jsonified, getParams
from couchpotato.core.helpers.variable import mergeDicts, md5, getExt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Quality, Profile, ProfileType
import os.path
import re
import time

log = CPLog(__name__)


class QualityPlugin(Plugin):

    qualities = [
        {'identifier': 'bd50', 'hd': True, 'size': (15000, 60000), 'label': 'BR-Disk', 'alternative': ['bd25'], 'allow': ['1080p'], 'ext':[], 'tags': ['bdmv', 'certificate', ('complete', 'bluray')]},
        {'identifier': '1080p', 'hd': True, 'size': (5000, 20000), 'label': '1080P', 'width': 1920, 'height': 1080, 'alternative': [], 'allow': [], 'ext':['mkv', 'm2ts'], 'tags': ['m2ts']},
        {'identifier': '720p', 'hd': True, 'size': (3500, 10000), 'label': '720P', 'width': 1280, 'height': 720, 'alternative': [], 'allow': [], 'ext':['mkv', 'ts']},
        {'identifier': 'brrip', 'hd': True, 'size': (700, 7000), 'label': 'BR-Rip', 'alternative': ['bdrip'], 'allow': ['720p'], 'ext':['avi']},
        {'identifier': 'dvdr', 'size': (3000, 10000), 'label': 'DVD-R', 'alternative': [], 'allow': [], 'ext':['iso', 'img'], 'tags': ['pal', 'ntsc', 'video_ts', 'audio_ts']},
        {'identifier': 'dvdrip', 'size': (600, 2400), 'label': 'DVD-Rip', 'width': 720, 'alternative': ['dvdrip'], 'allow': [], 'ext':['avi', 'mpg', 'mpeg'], 'tags': [('dvd', 'rip'), ('dvd', 'xvid'), ('dvd', 'divx')]},
        {'identifier': 'scr', 'size': (600, 1600), 'label': 'Screener', 'alternative': ['screener', 'dvdscr', 'ppvrip'], 'allow': ['dvdr', 'dvd'], 'ext':['avi', 'mpg', 'mpeg']},
        {'identifier': 'r5', 'size': (600, 1000), 'label': 'R5', 'alternative': [], 'allow': ['dvdr'], 'ext':['avi', 'mpg', 'mpeg']},
        {'identifier': 'tc', 'size': (600, 1000), 'label': 'TeleCine', 'alternative': ['telecine'], 'allow': [], 'ext':['avi', 'mpg', 'mpeg']},
        {'identifier': 'ts', 'size': (600, 1000), 'label': 'TeleSync', 'alternative': ['telesync', 'hdts'], 'allow': [], 'ext':['avi', 'mpg', 'mpeg']},
        {'identifier': 'cam', 'size': (600, 1000), 'label': 'Cam', 'alternative': ['camrip', 'hdcam'], 'allow': [], 'ext':['avi', 'mpg', 'mpeg']}
    ]
    pre_releases = ['cam', 'ts', 'tc', 'r5', 'scr']

    def __init__(self):
        addEvent('quality.all', self.all)
        addEvent('quality.single', self.single)
        addEvent('quality.guess', self.guess)
        addEvent('quality.pre_releases', self.preReleases)

        addApiView('quality.size.save', self.saveSize)
        addApiView('quality.list', self.allView, docs = {
            'desc': 'List all available qualities',
            'return': {'type': 'object', 'example': """{
            'success': True,
            'list': array, qualities
}"""}
        })

        addEvent('app.initialize', self.fill, priority = 10)

    def preReleases(self):
        return self.pre_releases

    def allView(self):

        return jsonified({
            'success': True,
            'list': self.all()
        })

    def all(self):

        db = get_session()

        qualities = db.query(Quality).all()

        temp = []
        for quality in qualities:
            q = mergeDicts(self.getQuality(quality.identifier), quality.to_dict())
            temp.append(q)

        return temp

    def single(self, identifier = ''):

        db = get_session()
        quality_dict = {}

        quality = db.query(Quality).filter_by(identifier = identifier).first()
        if quality:
            quality_dict = dict(self.getQuality(quality.identifier), **quality.to_dict())

        return quality_dict

    def getQuality(self, identifier):

        for q in self.qualities:
            if identifier == q.get('identifier'):
                return q

    def saveSize(self):

        params = getParams()

        db = get_session()
        quality = db.query(Quality).filter_by(identifier = params.get('identifier')).first()

        if quality:
            setattr(quality, params.get('value_type'), params.get('value'))
            db.commit()

        return jsonified({
            'success': True
        })

    def fill(self):

        db = get_session();

        order = 0
        for q in self.qualities:

            # Create quality
            qual = db.query(Quality).filter_by(identifier = q.get('identifier')).first()

            if not qual:
                log.info('Creating quality: %s', q.get('label'))
                qual = Quality()
                qual.order = order
                qual.identifier = q.get('identifier')
                qual.label = toUnicode(q.get('label'))
                qual.size_min, qual.size_max = q.get('size')

                db.add(qual)

            # Create single quality profile
            prof = db.query(Profile).filter(
                    Profile.core == True
                ).filter(
                    Profile.types.any(quality = qual)
                ).all()

            if not prof:
                log.info('Creating profile: %s', q.get('label'))
                prof = Profile(
                    core = True,
                    label = toUnicode(qual.label),
                    order = order
                )
                db.add(prof)

                profile_type = ProfileType(
                    quality = qual,
                    profile = prof,
                    finish = True,
                    order = 0
                )
                prof.types.append(profile_type)

            order += 1

        db.commit()

        time.sleep(0.3) # Wait a moment

        return True

    def guess(self, files, extra = {}):

        # Create hash for cache
        hash = md5(str([f.replace('.' + getExt(f), '') for f in files]))
        cached = self.getCache(hash)
        if cached and extra is {}: return cached

        for cur_file in files:
            size = (os.path.getsize(cur_file) / 1024 / 1024) if os.path.isfile(cur_file) else 0
            words = re.split('\W+', cur_file.lower())

            for quality in self.all():

                # Check tags
                if quality['identifier'] in words:
                    log.debug('Found via identifier "%s" in %s', (quality['identifier'], cur_file))
                    return self.setCache(hash, quality)

                if list(set(quality.get('alternative', [])) & set(words)):
                    log.debug('Found %s via alt %s in %s', (quality['identifier'], quality.get('alternative'), cur_file))
                    return self.setCache(hash, quality)

                for tag in quality.get('tags', []):
                    if isinstance(tag, tuple) and '.'.join(tag) in '.'.join(words):
                        log.debug('Found %s via tag %s in %s', (quality['identifier'], quality.get('tags'), cur_file))
                        return self.setCache(hash, quality)

                if list(set(quality.get('tags', [])) & set(words)):
                    log.debug('Found %s via tag %s in %s', (quality['identifier'], quality.get('tags'), cur_file))
                    return self.setCache(hash, quality)

        # Try again with loose testing
        quality = self.guessLoose(hash, extra = extra)
        if quality:
            return self.setCache(hash, quality)

        log.debug('Could not identify quality for: %s', files)
        return None

    def guessLoose(self, hash, extra):

        for quality in self.all():

            # Check width resolution, range 20
            if (quality.get('width', 720) - 20) <= extra.get('resolution_width', 0) <= (quality.get('width', 720) + 20):
                log.debug('Found %s via resolution_width: %s == %s', (quality['identifier'], quality.get('width', 720), extra.get('resolution_width', 0)))
                return self.setCache(hash, quality)

            # Check height resolution, range 20
            if (quality.get('height', 480) - 20) <= extra.get('resolution_height', 0) <= (quality.get('height', 480) + 20):
                log.debug('Found %s via resolution_height: %s == %s', (quality['identifier'], quality.get('height', 480), extra.get('resolution_height', 0)))
                return self.setCache(hash, quality)

        if 480 <= extra.get('resolution_width', 0) <= 720:
            log.debug('Found as dvdrip')
            return self.setCache(hash, self.single('dvdrip'))

        return None
