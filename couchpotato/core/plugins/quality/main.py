from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Quality, Profile, ProfileType
import os.path
import re

log = CPLog(__name__)


class QualityPlugin(Plugin):

    qualities = [
        {'identifier': 'bd50', 'size': (15000, 60000), 'label': 'BR-Disk', 'width': 1920, 'alternative': ['bd25'], 'allow': ['1080p'], 'ext':[], 'tags': ['x264', 'h264', 'bluray']},
        {'identifier': '1080p', 'size': (5000, 20000), 'label': '1080P', 'width': 1920, 'alternative': [], 'allow': [], 'ext':['mkv', 'm2ts'], 'tags': ['x264', 'h264', 'bluray']},
        {'identifier': '720p', 'size': (3500, 10000), 'label': '720P', 'width': 1280, 'alternative': [], 'allow': [], 'ext':['mkv', 'm2ts'], 'tags': ['x264', 'h264', 'bluray']},
        {'identifier': 'brrip', 'size': (700, 7000), 'label': 'BR-Rip', 'alternative': ['bdrip'], 'allow': ['720p'], 'ext':['avi']},
        {'identifier': 'dvdr', 'size': (3000, 10000), 'label': 'DVD-R', 'alternative': [], 'allow': [], 'ext':['iso', 'img'], 'tags': ['pal', 'ntsc']},
        {'identifier': 'dvdrip', 'size': (600, 2400), 'label': 'DVD-Rip', 'alternative': [], 'allow': [], 'ext':['avi', 'mpg', 'mpeg']},
        {'identifier': 'scr', 'size': (600, 1600), 'label': 'Screener', 'alternative': ['dvdscr'], 'allow': ['dvdr'], 'ext':['avi', 'mpg', 'mpeg']},
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
        addEvent('app.load', self.fill)

        self.registerStatic(__file__)

    def all(self):

        db = get_session()

        qualities = db.query(Quality).all()

        temp = []
        for quality in qualities:
            q = dict(self.getQuality(quality.identifier), **quality.to_dict())
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

    def guess(self, files, extra = {}):
        found = False

        for file in files:
            size = (os.path.getsize(file) / 1024 / 1024)
            words = re.split('\W+', file.lower())
            for quality in self.all():
                correctSize = False

                if size >= quality['size_min'] and size <= quality['size_max']:
                    correctSize = True

                # Check tags
                if type in words:
                    found = True

                for alt in quality.get('alternative'):
                    if alt in words:
                        found = True

                for tag in quality.get('tags', []):
                    if tag in words:
                        found = True

                # Check extension + filesize
                for ext in quality.get('ext'):
                    if ext in words and correctSize:
                        found = True

                # Last check on resolution only
                if quality.get('width', 480) == extra.get('resolution_width', 0):
                    found = True

                if found:
                    return quality

        return ''
