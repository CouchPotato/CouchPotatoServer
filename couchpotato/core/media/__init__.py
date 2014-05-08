import os
import traceback

from couchpotato import get_db, CPLog
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.plugins.base import Plugin
import six


log = CPLog(__name__)


class MediaBase(Plugin):

    _type = None

    def initType(self):
        addEvent('media.types', self.getType)

    def getType(self):
        return self._type

    def createOnComplete(self, media_id):

        def onComplete():
            try:
                media = fireEvent('media.get', media_id, single = True)
                event_name = '%s.searcher.single' % media.get('type')

                fireEventAsync(event_name, media, on_complete = self.createNotifyFront(media_id))
            except:
                log.error('Failed creating onComplete: %s', traceback.format_exc())

        return onComplete

    def createNotifyFront(self, media_id):

        def notifyFront():
            try:
                media = fireEvent('media.get', media_id, single = True)
                event_name = '%s.update' % media.get('type')

                fireEvent('notify.frontend', type = event_name, data = media)
            except:
                log.error('Failed creating onComplete: %s', traceback.format_exc())

        return notifyFront

    def getDefaultTitle(self, info, ):

        # Set default title
        default_title = toUnicode(info.get('title'))
        titles = info.get('titles', [])
        counter = 0
        def_title = None
        for title in titles:
            if (len(default_title) == 0 and counter == 0) or len(titles) == 1 or title.lower() == toUnicode(default_title.lower()) or (toUnicode(default_title) == six.u('') and toUnicode(titles[0]) == title):
                def_title = toUnicode(title)
                break
            counter += 1

        if not def_title:
            def_title = toUnicode(titles[0])

        return def_title or 'UNKNOWN'

    def getPoster(self, image_urls, existing_files):
        image_type = 'poster'

        # Remove non-existing files
        file_type = 'image_%s' % image_type

        # Make existing unique
        unique_files = list(set(existing_files.get(file_type, [])))

        # Remove files that can't be found
        for ef in unique_files:
            if not os.path.isfile(ef):
                unique_files.remove(ef)

        # Replace new files list
        existing_files[file_type] = unique_files
        if len(existing_files) == 0:
            del existing_files[file_type]

        # Loop over type
        for image in image_urls.get(image_type, []):
            if not isinstance(image, (str, unicode)):
                continue

            if file_type not in existing_files or len(existing_files.get(file_type, [])) == 0:
                file_path = fireEvent('file.download', url = image, single = True)
                if file_path:
                    existing_files[file_type] = [file_path]
                    break
            else:
                break
