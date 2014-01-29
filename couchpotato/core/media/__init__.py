import traceback
from couchpotato import get_session, get_db, CPLog
from couchpotato.core.event import addEvent, fireEventAsync, fireEvent
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Media

log = CPLog(__name__)


class MediaBase(Plugin):

    _type = None

    default_dict = {
        'profile': {'types': {'quality': {}}},
        'releases': {'status': {}, 'quality': {}, 'files': {}, 'info': {}},
        'library': {'titles': {}, 'files': {}},
        'files': {},
        'status': {},
        'category': {},
    }

    def initType(self):
        addEvent('media.types', self.getType)

    def getType(self):
        return self._type

    def createOnComplete(self, media_id):

        def onComplete():
            try:
                db = get_db()
                media = db.get('id', media_id)
                event_name = '%s.searcher.single' % media.get('type')

                fireEvent(event_name, media, on_complete = self.createNotifyFront(media_id))
            except:
                log.error('Failed creating onComplete: %s', traceback.format_exc())
            finally:
                pass  #db.close()

        return onComplete

    def createNotifyFront(self, media_id):

        def notifyFront():
            try:
                db = get_db()
                media = db.get('id', media_id)
                event_name = '%s.update' % media.get('type')

                fireEvent('notify.frontend', type = event_name, data = media)
            except:
                log.error('Failed creating onComplete: %s', traceback.format_exc())
            finally:
                pass  #db.close()

        return notifyFront
