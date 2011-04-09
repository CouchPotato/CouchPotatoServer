from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEventAsync, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Library, LibraryTitle

log = CPLog(__name__)

class LibraryPlugin(Plugin):

    def __init__(self):
        addEvent('library.add', self.add)
        addEvent('library.update', self.update)

    def add(self, attrs = {}):

        db = get_session()

        l = db.query(Library).filter_by(identifier = attrs.get('identifier')).first()
        if not l:
            l = Library(
                year = attrs.get('year'),
                identifier = attrs.get('identifier'),
                plot = attrs.get('plot'),
                tagline = attrs.get('tagline')
            )

            title = LibraryTitle(
                title = attrs.get('title')
            )

            l.titles.append(title)

            db.add(l)
            db.commit()

        # Update library info
        fireEventAsync('library.update', library = l, default_title = attrs.get('title', ''))

        #db.remove()
        return l

    def update(self, library, default_title = ''):

        db = get_session()
        library = db.query(Library).filter_by(identifier = library.identifier).first()

        info = fireEvent('provider.movie.info', merge = True, identifier = library.identifier)

        # Main info
        library.plot = info.get('plot', '')
        library.tagline = info.get('tagline', '')
        library.year = info.get('year', 0)

        # Titles
        [db.delete(title) for title in library.titles]
        titles = info.get('titles')

        log.debug('Adding titles: %s' % titles)
        for title in titles:
            t = LibraryTitle(
                title = title,
                default = title.lower() == default_title.lower()
            )
            library.titles.append(t)

        db.commit()

        # Files
        images = info.get('images')
        for type in images:
            for image in images[type]:
                file_path = fireEvent('file.download', url = image, single = True)
                file = fireEvent('file.add', path = file_path, type = ('image', type[:-1]), single = True)
                try:
                    library.files.append(file)
                    db.commit()
                except:
                    log.debug('File already attached to library')

        fireEvent('library.update.after')
