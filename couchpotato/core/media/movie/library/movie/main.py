from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEventAsync, fireEvent
from couchpotato.core.helpers.encoding import toUnicode, simplifyString
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.library import LibraryBase
from couchpotato.core.settings.model import Library, LibraryTitle, File
from string import ascii_letters
import time
import traceback
import six

log = CPLog(__name__)


class MovieLibraryPlugin(LibraryBase):

    default_dict = {'titles': {}, 'files': {}}

    def __init__(self):
        addEvent('library.add.movie', self.add)
        addEvent('library.update.movie', self.update)
        addEvent('library.update.movie.release_date', self.updateReleaseDate)

    def add(self, attrs = None, update_after = True):
        if not attrs: attrs = {}

        primary_provider = attrs.get('primary_provider', 'imdb')

        try:
            db = get_session()

            l = db.query(Library).filter_by(identifier = attrs.get('identifier')).first()
            if not l:
                status = fireEvent('status.get', 'needs_update', single = True)
                l = Library(
                    year = attrs.get('year'),
                    identifier = attrs.get('identifier'),
                    plot = toUnicode(attrs.get('plot')),
                    tagline = toUnicode(attrs.get('tagline')),
                    status_id = status.get('id'),
                    info = {}
                )

                title = LibraryTitle(
                    title = toUnicode(attrs.get('title')),
                    simple_title = self.simplifyTitle(attrs.get('title')),
                )

                l.titles.append(title)

                db.add(l)
                db.commit()

            # Update library info
            if update_after is not False:
                handle = fireEventAsync if update_after is 'async' else fireEvent
                handle('library.update.movie', identifier = l.identifier, default_title = toUnicode(attrs.get('title', '')))

            library_dict = l.to_dict(self.default_dict)
            return library_dict
        except:
            log.error('Failed adding media: %s', traceback.format_exc())
            db.rollback()
        finally:
            db.close()

        return {}

    def update(self, identifier, default_title = '', extended = False):

        if self.shuttingDown():
            return

        try:
            db = get_session()

            library = db.query(Library).filter_by(identifier = identifier).first()
            done_status = fireEvent('status.get', 'done', single = True)

            info = fireEvent('movie.info', merge = True, extended = extended, identifier = identifier)

            # Don't need those here
            try: del info['in_wanted']
            except: pass
            try: del info['in_library']
            except: pass

            if not info or len(info) == 0:
                log.error('Could not update, no movie info to work with: %s', identifier)
                return False

            # Main info
            library.plot = toUnicode(info.get('plot', ''))
            library.tagline = toUnicode(info.get('tagline', ''))
            library.year = info.get('year', 0)
            library.status_id = done_status.get('id')
            library.info.update(info)
            db.commit()

            # Titles
            [db.delete(title) for title in library.titles]
            db.commit()

            titles = info.get('titles', [])
            log.debug('Adding titles: %s', titles)
            counter = 0

            def_title = None
            for title in titles:
                if (len(default_title) == 0 and counter == 0) or len(titles) == 1 or title.lower() == toUnicode(default_title.lower()) or (toUnicode(default_title) == six.u('') and toUnicode(titles[0]) == title):
                    def_title = toUnicode(title)
                    break
                counter += 1

            if not def_title:
                def_title = toUnicode(titles[0])

            for title in titles:
                if not title:
                    continue
                title = toUnicode(title)
                t = LibraryTitle(
                    title = title,
                    simple_title = self.simplifyTitle(title),
                    default = title == def_title
                )
                library.titles.append(t)

            db.commit()

            # Files
            images = info.get('images', [])
            for image_type in ['poster']:
                for image in images.get(image_type, []):
                    if not isinstance(image, (str, unicode)):
                        continue

                    file_path = fireEvent('file.download', url = image, single = True)
                    if file_path:
                        file_obj = fireEvent('file.add', path = file_path, type_tuple = ('image', image_type), single = True)
                        try:
                            file_obj = db.query(File).filter_by(id = file_obj.get('id')).one()
                            library.files.append(file_obj)
                            db.commit()

                            break
                        except:
                            log.debug('Failed to attach to library: %s', traceback.format_exc())
                            db.rollback()

            library_dict = library.to_dict(self.default_dict)
            return library_dict
        except:
            log.error('Failed update media: %s', traceback.format_exc())
            db.rollback()
        finally:
            db.close()

        return {}

    def updateReleaseDate(self, identifier):

        try:
            db = get_session()
            library = db.query(Library).filter_by(identifier = identifier).first()

            if not library.info:
                library_dict = self.update(identifier)
                dates = library_dict.get('info', {}).get('release_date')
            else:
                dates = library.info.get('release_date')

            if dates and (dates.get('expires', 0) < time.time() or dates.get('expires', 0) > time.time() + (604800 * 4)) or not dates:
                dates = fireEvent('movie.release_date', identifier = identifier, merge = True)
                library.info.update({'release_date': dates})
                db.commit()

            return dates
        except:
            log.error('Failed updating release dates: %s', traceback.format_exc())
            db.rollback()
        finally:
            db.close()

        return {}


    def simplifyTitle(self, title):

        title = toUnicode(title)

        nr_prefix = '' if title[0] in ascii_letters else '#'
        title = simplifyString(title)

        for prefix in ['the ']:
            if prefix == title[:len(prefix)]:
                title = title[len(prefix):]
                break

        return nr_prefix + title
