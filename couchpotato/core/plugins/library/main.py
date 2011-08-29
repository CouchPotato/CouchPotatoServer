from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEventAsync, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Library, LibraryTitle, File
import traceback

log = CPLog(__name__)

class LibraryPlugin(Plugin):

    default_dict = {'titles': {}, 'files':{}, 'info':{}}

    def __init__(self):
        addEvent('library.add', self.add)
        addEvent('library.update', self.update)

    def add(self, attrs = {}, update_after = True):

        db = get_session()

        l = db.query(Library).filter_by(identifier = attrs.get('identifier')).first()
        if not l:
            status = fireEvent('status.get', 'needs_update', single = True)
            l = Library(
                year = attrs.get('year'),
                identifier = attrs.get('identifier'),
                plot = attrs.get('plot'),
                tagline = attrs.get('tagline'),
                status_id = status.get('id')
            )

            title = LibraryTitle(
                title = attrs.get('title')
            )

            l.titles.append(title)

            db.add(l)
            db.commit()

        # Update library info
        if update_after:
            fireEventAsync('library.update', identifier = l.identifier, default_title = attrs.get('title', ''))

        return l.to_dict(self.default_dict)

    def update(self, identifier, default_title = '', force = False):

        db = get_session()
        library = db.query(Library).filter_by(identifier = identifier).first()
        done_status = fireEvent('status.get', 'done', single = True)

        library_dict = library.to_dict(self.default_dict)
        do_update = True

        if library.status_id == done_status.get('id') and not force:
            do_update = False
        else:
            info = fireEvent('provider.movie.info', merge = True, identifier = identifier)
            if not info or len(info) == 0:
                log.error('Could not update, no movie info to work with: %s' % identifier)
                do_update = False

        # Main info
        if do_update:
            library.plot = info.get('plot', '')
            library.tagline = info.get('tagline', '')
            library.year = info.get('year', 0)
            library.status_id = done_status.get('id')
            db.commit()

            # Titles
            [db.delete(title) for title in library.titles]
            db.commit()

            titles = info.get('titles', [])

            log.debug('Adding titles: %s' % titles)
            for title in titles:
                t = LibraryTitle(
                    title = title,
                    default = title.lower() == default_title.lower()
                )
                library.titles.append(t)

            db.commit()

            # Files
            images = info.get('images', [])
            for type in images:
                for image in images[type]:
                    if not isinstance(image, str):
                        continue

                    file_path = fireEvent('file.download', url = image, single = True)
                    file = fireEvent('file.add', path = file_path, type = ('image', type[:-1]), single = True)
                    try:
                        file = db.query(File).filter_by(id = file.get('id')).one()
                        library.files.append(file)
                        db.commit()
                    except:
                        log.debug('Failed to attach to library: %s' % traceback.format_exc())

            library_dict = library.to_dict(self.default_dict)

        fireEvent('library.update_finish', data = library_dict)

        return library_dict
