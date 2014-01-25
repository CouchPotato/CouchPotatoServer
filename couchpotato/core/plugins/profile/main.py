import traceback
from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Profile, ProfileType, Media
from sqlalchemy.orm import joinedload_all

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

        addEvent('app.initialize', self.fill, priority = 90)
        addEvent('app.load', self.forceDefaults)

    def forceDefaults(self):

        # Get all active movies without profile
        active_status = fireEvent('status.get', 'active', single = True)

        try:
            db = get_session()
            movies = db.query(Media).filter(Media.status_id == active_status.get('id'), Media.profile == None).all()

            if len(movies) > 0:
                default_profile = self.default()
                for movie in movies:
                    movie.profile_id = default_profile.get('id')
                    db.commit()
        except:
            log.error('Failed: %s', traceback.format_exc())
            db.rollback()
        finally:
            db.close()

    def allView(self, **kwargs):

        return {
            'success': True,
            'list': self.all()
        }

    def all(self):

        db = get_session()
        profiles = db.query(Profile) \
            .options(joinedload_all('types')) \
            .all()

        temp = []
        for profile in profiles:
            temp.append(profile.to_dict(self.to_dict))

        return temp

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
            db.close()

        return {
            'success': False
        }

    def default(self):

        db = get_session()
        default = db.query(Profile) \
            .options(joinedload_all('types')) \
            .first()
        default_dict = default.to_dict(self.to_dict)

        return default_dict

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
            db.close()

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
            db.close()

        return {
            'success': False
        }

    def fill(self):

        try:
            db = get_session()

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
            order = -2
            for profile in profiles:
                log.info('Creating default profile: %s', profile.get('label'))
                p = Profile(
                    label = toUnicode(profile.get('label')),
                    order = order
                )
                db.add(p)

                quality_order = 0
                for quality in profile.get('qualities'):
                    quality = fireEvent('quality.single', identifier = quality, single = True)
                    profile_type = ProfileType(
                        quality_id = quality.get('id'),
                        profile = p,
                        finish = True,
                        wait_for = 0,
                        order = quality_order
                    )
                    p.types.append(profile_type)

                    quality_order += 1

                order += 1

            db.commit()

            return True
        except:
            log.error('Failed: %s', traceback.format_exc())
            db.rollback()
        finally:
            db.close()

        return False
