import traceback

from couchpotato import get_db, tryInt
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from .index import ProfileIndex


log = CPLog(__name__)


class ProfilePlugin(Plugin):

    _database = {
        'profile': ProfileIndex
    }

    def __init__(self):
        addEvent('profile.all', self.all)
        addEvent('profile.default', self.default)

        addApiView('profile.save', self.save)
        addApiView('profile.save_order', self.saveOrder)
        addApiView('profile.delete', self.delete)
        addApiView('profile.list', self.allView, docs = {
            'desc': 'List all available profiles',
            'return': {'type': 'object', 'example': """{
            'success': True,
            'list': array, profiles
}"""}
        })

        addEvent('app.initialize', self.fill, priority = 90)
        addEvent('app.load', self.forceDefaults, priority = 110)

    def forceDefaults(self):

        db = get_db()

        # Fill qualities and profiles if they are empty somehow..
        if db.count(db.all, 'profile') == 0:

            if db.count(db.all, 'quality') == 0:
                fireEvent('quality.fill', single = True)

            self.fill()

        # Get all active movies without profile
        try:
            medias = fireEvent('media.with_status', 'active', single = True)

            profile_ids = [x.get('_id') for x in self.all()]
            default_id = profile_ids[0]

            for media in medias:
                if media.get('profile_id') not in profile_ids:
                    media['profile_id'] = default_id
                    db.update(media)
        except:
            log.error('Failed: %s', traceback.format_exc())

        # Cleanup profiles that have empty qualites
        profiles = self.all()
        for profile in profiles:
            try:
                if '' in profile.get('qualities') or '-1' in profile.get('qualities'):
                    log.warning('Found profile with empty qualities, cleaning it up')
                    p = db.get('id', profile.get('_id'))
                    p['qualities'] = [x for x in p['qualities'] if (x != '' and x != '-1')]
                    db.update(p)
            except:
                log.error('Failed: %s', traceback.format_exc())

    def allView(self, **kwargs):

        return {
            'success': True,
            'list': self.all()
        }

    def all(self):

        db = get_db()
        profiles = db.all('profile', with_doc = True)

        return [x['doc'] for x in profiles]

    def save(self, **kwargs):

        try:
            db = get_db()

            profile = {
                '_t': 'profile',
                'label': toUnicode(kwargs.get('label')),
                'order': tryInt(kwargs.get('order', 999)),
                'core': kwargs.get('core', False),
                'minimum_score': tryInt(kwargs.get('minimum_score', 1)),
                'qualities': [],
                'wait_for': [],
                'stop_after': [],
                'finish': [],
                '3d': []
            }

            # Update types
            order = 0
            for type in kwargs.get('types', []):
                profile['qualities'].append(type.get('quality'))
                profile['wait_for'].append(tryInt(kwargs.get('wait_for', 0)))
                profile['stop_after'].append(tryInt(kwargs.get('stop_after', 0)))
                profile['finish'].append((tryInt(type.get('finish')) == 1) if order > 0 else True)
                profile['3d'].append(tryInt(type.get('3d')))
                order += 1

            id = kwargs.get('id')
            try:
                p = db.get('id', id)
                profile['order'] = tryInt(kwargs.get('order', p.get('order', 999)))
            except:
                p = db.insert(profile)

            p.update(profile)
            db.update(p)

            return {
                'success': True,
                'profile': p
            }
        except:
            log.error('Failed: %s', traceback.format_exc())

        return {
            'success': False
        }

    def default(self):
        db = get_db()
        return list(db.all('profile', limit = 1, with_doc = True))[0]['doc']

    def saveOrder(self, **kwargs):

        try:
            db = get_db()

            order = 0

            for profile_id in kwargs.get('ids', []):
                p = db.get('id', profile_id)
                p['hide'] = tryInt(kwargs.get('hidden')[order]) == 1
                p['order'] = order
                db.update(p)

                order += 1

            return {
                'success': True
            }
        except:
            log.error('Failed: %s', traceback.format_exc())

        return {
            'success': False
        }

    def delete(self, id = None, **kwargs):

        try:
            db = get_db()

            success = False
            message = ''

            try:
                p = db.get('id', id)
                db.delete(p)

                # Force defaults on all empty profile movies
                self.forceDefaults()

                success = True
            except Exception as e:
                message = log.error('Failed deleting Profile: %s', e)

            return {
                'success': success,
                'message': message
            }
        except:
            log.error('Failed: %s', traceback.format_exc())

        return {
            'success': False
        }

    def fill(self):

        try:
            db = get_db()

            profiles = [{
                'label': 'Best',
                'qualities': ['720p', '1080p', 'brrip', 'dvdrip']
            }, {
                'label': 'HD',
                'qualities': ['720p', '1080p']
            }, {
                'label': 'SD',
                'qualities': ['dvdrip', 'dvdr']
            }, {
                'label': 'Prefer 3D HD',
                'qualities': ['1080p', '720p', '720p', '1080p'],
                '3d': [True, True]
            }, {
                'label': '3D HD',
                'qualities': ['1080p', '720p'],
                '3d': [True, True]
            }, {
                'label': 'UHD 4K',
                'qualities': ['720p', '1080p', '2160p']
            }]

            # Create default quality profile
            order = 0
            for profile in profiles:
                log.info('Creating default profile: %s', profile.get('label'))

                pro = {
                    '_t': 'profile',
                    'label': toUnicode(profile.get('label')),
                    'order': order,
                    'qualities': profile.get('qualities'),
                    'minimum_score': 1,
                    'finish': [],
                    'wait_for': [],
                    'stop_after': [],
                    '3d': []
                }

                threed = profile.get('3d', [])
                for q in profile.get('qualities'):
                    pro['finish'].append(True)
                    pro['wait_for'].append(0)
                    pro['stop_after'].append(0)
                    pro['3d'].append(threed.pop() if threed else False)

                db.insert(pro)
                order += 1

            return True
        except:
            log.error('Failed: %s', traceback.format_exc())

        return False
