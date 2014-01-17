from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEventAsync, fireEvent
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Media


class MediaBase(Plugin):

    _type = None

    default_dict = {
        'profile': {'types': {'quality': {}}},
        'releases': {'status': {}, 'quality': {}, 'files':{}, 'info': {}},
        'library': {'titles': {}, 'files':{}},
        'files': {},
        'status': {},
        'category': {},
    }

    def initType(self):
        addEvent('media.types', self.getType)

    def getType(self):
        return self._type

    def createOnComplete(self, id):

        def onComplete():
            db = get_session()
            media = db.query(Media).filter_by(id = id).first()
            media_dict = media.to_dict(self.default_dict)
            event_name = '%s.searcher.single' % media.type
            db.expire_all()

            fireEvent(event_name, media_dict, on_complete = self.createNotifyFront(id))

        return onComplete

    def createNotifyFront(self, media_id):

        def notifyFront():
            db = get_session()
            media = db.query(Media).filter_by(id = media_id).first()
            media_dict = media.to_dict(self.default_dict)
            event_name = '%s.update' % media.type
            db.expire_all()

            fireEvent('notify.frontend', type = event_name, data = media_dict)

        return notifyFront
