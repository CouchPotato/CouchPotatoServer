import traceback

from CodernityDB.database import RecordNotFound
from couchpotato import get_db
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode, ss
from couchpotato.core.helpers.variable import mergeDicts, getExt, tryInt, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class QualityBase(Plugin):
    type = None

    properties = {}
    qualities = []

    pre_releases = ['cam', 'ts', 'tc', 'r5', 'scr']
    threed_tags = {
        'sbs': [('half', 'sbs'), 'hsbs', ('full', 'sbs'), 'fsbs'],
        'ou': [('half', 'ou'), 'hou', ('full', 'ou'), 'fou'],
        '3d': ['2d3d', '3d2d', '3d'],
    }

    cached_qualities = None
    cached_order = None

    def __init__(self):
        addEvent('quality.pre_releases', self.preReleases)

        addEvent('quality.get', self.get)
        addEvent('quality.all', self.all)
        addEvent('quality.reset_cache', self.resetCache)

        addEvent('quality.fill', self.fill)
        addEvent('quality.isfinish', self.isFinish)
        addEvent('quality.ishigher', self.isHigher)

        addEvent('app.initialize', self.fill, priority = 10)

        self.order = []

        for q in self.qualities:
            self.order.append(q.get('identifier'))

    def preReleases(self, types = None):
        if types and self.type not in types:
            return

        return self.pre_releases

    def get(self, identifier, types = None):
        if types and self.type not in types:
            return

        for q in self.qualities:
            if identifier == q.get('identifier'):
                return q

    def all(self, types = None):
        if types and self.type not in types:
            return

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

    def expand(self, quality):
        for key, options in self.properties.items():
            if key not in quality:
                continue

            quality[key] = [self.getProperty(key, identifier) for identifier in quality[key]]

        return quality

    def getProperty(self, key, identifier):
        if key not in self.properties:
            return

        for item in self.properties[key]:
            if item.get('identifier') == identifier:
                return item

    def resetCache(self):
        self.cached_qualities = None

    def fill(self):

        try:
            db = get_db()

            order = 0
            for q in self.qualities:

                existing = None
                try:
                    existing = db.get('quality', q.get('identifier'))
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

                order += 1

            return True
        except:
            log.error('Failed: %s', traceback.format_exc())

        return False

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
