from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.request import jsonified, getParams, getParam
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
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

        addEvent('app.initialize', self.fill, priority = 90)

    def allView(self):

        return jsonified({
            'success': True,
            'list': self.all()
        })

    def all(self):

        db = get_session()
        profiles = db.query(Profile).all()

        temp = []
        for profile in profiles:
            temp.append(profile.to_dict(self.to_dict))

        #db.close()
        return temp

    def save(self):

        params = getParams()

        db = get_session()

        p = db.query(Profile).filter_by(id = params.get('id')).first()
        if not p:
            p = Profile()
            db.add(p)

        p.label = toUnicode(params.get('label'))
        p.order = params.get('order', p.order if p.order else 0)
        p.core = params.get('core', False)

        #delete old types
        [db.delete(t) for t in p.types]

        order = 0
        for type in params.get('types', []):
            t = ProfileType(
                order = order,
                finish = type.get('finish') if order > 0 else 1,
                wait_for = params.get('wait_for'),
                quality_id = type.get('quality_id')
            )
            p.types.append(t)

            order += 1

        db.commit()

        profile_dict = p.to_dict(self.to_dict)

        #db.close()
        return jsonified({
            'success': True,
            'profile': profile_dict
        })

    def default(self):

        db = get_session()
        default = db.query(Profile).first()
        default_dict = default.to_dict(self.to_dict)
        #db.close()

        return default_dict

    def saveOrder(self):

        params = getParams()
        db = get_session()

        order = 0
        for profile in params.get('ids', []):
            p = db.query(Profile).filter_by(id = profile).first()
            p.hide = params.get('hidden')[order]
            p.order = order

            order += 1

        db.commit()
        #db.close()

        return jsonified({
            'success': True
        })

    def delete(self):

        id = getParam('id')

        db = get_session()

        success = False
        message = ''
        try:
            p = db.query(Profile).filter_by(id = id).first()

            db.delete(p)
            db.commit()

            success = True
        except Exception, e:
            message = log.error('Failed deleting Profile: %s', e)

        #db.close()

        return jsonified({
            'success': success,
            'message': message
        })

    def fill(self):

        db = get_session();

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

                db.commit()
                quality_order += 1

            order += 1

        #db.close()
        return True
