import traceback
from couchpotato import get_session, get_db
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from .index import ProfileIndex
from couchpotato.core.settings.model import Profile, ProfileType

log = CPLog(__name__)


class ProfilePlugin(Plugin):

    to_dict = {'types': {}}

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

        addEvent('database.setup', self.databaseSetup)

        addEvent('app.initialize', self.fill, priority = 90)
        addEvent('app.load', self.forceDefaults)

    def databaseSetup(self):

        db = get_db()

        try:
            db.add_index(ProfileIndex(db.path, 'profile'))
        except:
            log.debug('Index already exists')
            db.edit_index(ProfileIndex(db.path, 'profile'))

    def forceDefaults(self):

        # Get all active movies without profile
        try:
            db = get_db()
            medias = db.run('media', 'with_status', ['active'])

            profile_ids = [x.get('_id') for x in self.all()]

            for media in medias:
                if media.get('profile_id') not in profile_ids:
                    media['profile_id'] = profile_ids[0].get('_id')
                    db.update(media)
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
            db = get_session()

            p = db.query(Profile).filter_by(id = kwargs.get('id')).first()
            if not p:
                p = Profile()
                db.add(p)

            p.label = toUnicode(kwargs.get('label'))
            p.order = kwargs.get('order', p.order if p.order else 0)
            p.core = kwargs.get('core', False)

            #delete old types
            [db.delete(t) for t in p.types]

            order = 0
            for type in kwargs.get('types', []):
                t = ProfileType(
                    order = order,
                    finish = type.get('finish') if order > 0 else 1,
                    wait_for = kwargs.get('wait_for'),
                    quality_id = type.get('quality_id')
                )
                p.types.append(t)

                order += 1

            db.commit()

            profile_dict = p.to_dict(self.to_dict)

            return {
                'success': True,
                'profile': profile_dict
            }
        except:
            log.error('Failed: %s', traceback.format_exc())
            db.rollback()
        finally:
            pass  #db.close()

        return {
            'success': False
        }

    def default(self):
        db = get_db()
        return list(db.all('profile', limit = 1, with_doc = True))[0]['doc']

    def saveOrder(self, **kwargs):

        try:
            db = get_session()

            order = 0
            for profile in kwargs.get('ids', []):
                p = db.query(Profile).filter_by(id = profile).first()
                p.hide = kwargs.get('hidden')[order]
                p.order = order

                order += 1

            db.commit()

            return {
                'success': True
            }
        except:
            log.error('Failed: %s', traceback.format_exc())
            db.rollback()
        finally:
            pass  #db.close()

        return {
            'success': False
        }

    def delete(self, id = None, **kwargs):

        try:
            db = get_session()

            success = False
            message = ''
            try:
                p = db.query(Profile).filter_by(id = id).first()

                db.delete(p)
                db.commit()

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
            db.rollback()
        finally:
            pass  #db.close()

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
                    'finish': [],
                    'wait_for': []
                }

                for q in profile.get('qualities'):
                    pro['finish'].append(True)
                    pro['wait_for'].append(0)

                db.insert(pro)
                order += 1

            return True
        except:
            log.error('Failed: %s', traceback.format_exc())

        return False
