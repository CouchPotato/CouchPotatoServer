from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.request import jsonified, getParams, getParam
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Profile, ProfileType

log = CPLog(__name__)


class ProfilePlugin(Plugin):

    def __init__(self):
        addEvent('profile.all', self.all)

        addApiView('profile.save', self.save)
        addApiView('profile.delete', self.delete)

        path = self.registerStatic(__file__)
        fireEvent('register_script', path + 'profile.js')
        fireEvent('register_style', path + 'profile.css')

    def all(self):

        db = get_session()
        profiles = db.query(Profile).all()

        temp = []
        for profile in profiles:
            temp.append(profile.to_dict(deep = {'types': {}}))

        return temp

    def save(self):

        params = getParams()

        db = get_session()

        p = db.query(Profile).filter_by(id = params.get('id')).first()
        if not p:
            p = Profile()
            db.add(p)

        p.label = params.get('label')
        p.order = params.get('order', p.order if p.order else 0)
        p.core = params.get('core', False)

        #delete old types
        [db.delete(t) for t in p.types]

        order = 0
        for type in params.get('types', []):
            t = ProfileType(
                order = order,
                finish = type.get('finish'),
                wait_for = params.get('wait_for'),
                quality_id = type.get('quality_id')
            )
            p.types.append(t)

            order += 1

        db.commit()

        profile_dict = p.to_dict(deep = {'types': {}})

        return jsonified({
            'success': True,
            'profile': profile_dict
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
            message = 'Failed deleting Profile: %s' % e
            log.error(message)

        return jsonified({
            'success': success,
            'message': message
        })
