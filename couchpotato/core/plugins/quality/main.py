from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.request import jsonified, getParams
from couchpotato.core.helpers.variable import mergeDicts, md5
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Quality, Profile, ProfileType
import os.path
import re

log = CPLog(__name__)


class QualityPlugin(Plugin):

    qualities = [
        {'identifier': 'bd50', 'hd': True, 'size': (15000, 60000), 'label': 'BR-Disk', 'width': 1920, 'alternative': ['bd25'], 'allow': ['1080p'], 'ext':[], 'tags': ['bdmv', 'certificate']},
        {'identifier': '1080p', 'hd': True, 'size': (5000, 20000), 'label': '1080P', 'width': 1920, 'alternative': [], 'allow': [], 'ext':['mkv', 'm2ts']},
        {'identifier': '720p', 'hd': True, 'size': (3500, 10000), 'label': '720P', 'width': 1280, 'alternative': [], 'allow': [], 'ext':['mkv', 'm2ts']},
        {'identifier': 'brrip', 'hd': True, 'size': (700, 7000), 'label': 'BR-Rip', 'alternative': ['bdrip'], 'allow': ['720p'], 'ext':['avi']},
        {'identifier': 'dvdr', 'size': (3000, 10000), 'label': 'DVD-R', 'alternative': [], 'allow': [], 'ext':['iso', 'img'], 'tags': ['pal', 'ntsc', 'video_ts', 'audio_ts']},
        {'identifier': 'dvdrip', 'size': (600, 2400), 'label': 'DVD-Rip', 'alternative': ['dvdrip'], 'allow': [], 'ext':['avi', 'mpg', 'mpeg']},
        {'identifier': 'scr', 'size': (600, 1600), 'label': 'Screener', 'alternative': ['dvdscr', 'ppvrip'], 'allow': ['dvdr'], 'ext':['avi', 'mpg', 'mpeg']},
        {'identifier': 'r5', 'size': (600, 1000), 'label': 'R5', 'alternative': [], 'allow': ['dvdr'], 'ext':['avi', 'mpg', 'mpeg']},
        {'identifier': 'tc', 'size': (600, 1000), 'label': 'TeleCine', 'alternative': ['telecine'], 'allow': [], 'ext':['avi', 'mpg', 'mpeg']},
        {'identifier': 'ts', 'size': (600, 1000), 'label': 'TeleSync', 'alternative': ['telesync'], 'allow': [], 'ext':['avi', 'mpg', 'mpeg']},
        {'identifier': 'cam', 'size': (600, 1000), 'label': 'Cam', 'alternative': [], 'allow': [], 'ext':['avi', 'mpg', 'mpeg']}
    ]
    pre_releases = ['cam', 'ts', 'tc', 'r5', 'scr']

    def __init__(self):
        addEvent('quality.all', self.all)
        addEvent('quality.single', self.single)
        addEvent('quality.guess', self.guess)

        addApiView('quality.size.save', self.saveSize)

        addEvent('app.initialize', self.fill, priority = 10)

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
            quality = db.query(Quality).filter_by(identifier = q.get('identifier')).first()

            if not quality:
                log.info('Creating quality: %s' % q.get('label'))
                quality = Quality()
                db.add(quality)

            quality.order = order
            quality.identifier = q.get('identifier')
            quality.label = q.get('label')
            quality.size_min, quality.size_max = q.get('size')

            # Create single quality profile
            profile = db.query(Profile).filter(
                    Profile.core == True
                ).filter(
                    Profile.types.any(quality = quality)
                ).all()

            if not profile:
                log.info('Creating profile: %s' % q.get('label'))
                profile = Profile(
                    core = True,
                    label = toUnicode(quality.label),
                    order = order
                )
                db.add(profile)

                profile_type = ProfileType(
                    quality = quality,
                    profile = profile,
                    finish = True,
                    order = 0
                )
                profile.types.append(profile_type)

            order += 1
            db.commit()

        return True

    def guess(self, files, extra = {}, loose = False):

        # Create hash for cache
        hash = md5(str(files))
        cached = self.getCache(hash)
        if cached: return cached

        for cur_file in files:
            size = (os.path.getsize(cur_file) / 1024 / 1024) if os.path.isfile(cur_file) else 0
            words = re.split('\W+', cur_file.lower())

            for quality in self.all():

                # Check tags
                if quality['identifier'] in words:
                    log.debug('Found via identifier "%s" in %s' % (quality['identifier'], file))
                    return self.setCache(hash, quality)

                if list(set(quality.get('alternative', [])) & set(words)):
                    log.debug('Found %s via alt %s in %s' % (quality['identifier'], quality.get('alternative'), file))
                    return self.setCache(hash, quality)

                if list(set(quality.get('tags', [])) & set(words)):
                    log.debug('Found %s via tag %s in %s' % (quality['identifier'], quality.get('tags'), file))
                    return self.setCache(hash, quality)

                # Check on unreliable stuff
                if loose:
                    # Check extension + filesize
                    if list(set(quality.get('ext', [])) & set(words)) and size >= quality['size_min'] and size <= quality['size_max']:
                        log.debug('Found %s via ext %s in %s' % (quality['identifier'], quality.get('ext'), words))
                        return self.setCache(hash, quality)

                    # Last check on resolution only
                    if quality.get('width', 480) == extra.get('resolution_width', 0):
                        log.debug('Found %s via resolution_width: %s == %s' % (quality['identifier'], quality.get('width', 480), extra.get('resolution_width', 0)))
                        return self.setCache(hash, quality)


        # Try again with loose testing
        if not loose:
            quality = self.guess(files, extra = extra, loose = True)
            if quality:
                return self.setCache(hash, quality)

        log.error('Could not identify quality for: %s' % files)
        return self.setCache(hash, quality)
