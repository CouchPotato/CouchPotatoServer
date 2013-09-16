from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEventAsync, fireEvent
from couchpotato.core.helpers.encoding import toUnicode, simplifyString
from couchpotato.core.logger import CPLog
from couchpotato.core.settings.model import SeasonLibrary, ShowLibrary, LibraryTitle, File
from couchpotato.core.media._base.library import LibraryBase
from couchpotato.core.helpers.variable import tryInt
from string import ascii_letters
import time
import traceback

log = CPLog(__name__)


class SeasonLibraryPlugin(LibraryBase):

    default_dict = {'titles': {}, 'files':{}}

    def __init__(self):
        addEvent('library.add.season', self.add)
        addEvent('library.update.season', self.update)
        addEvent('library.update.season_release_date', self.updateReleaseDate)

    def add(self, attrs = {}, update_after = True):
        type = attrs.get('type', 'season')
        primary_provider = attrs.get('primary_provider', 'thetvdb')

        db = get_session()
        parent_identifier = attrs.get('parent_identifier',  None)

        parent = None
        if parent_identifier:
            parent = db.query(ShowLibrary).filter_by(primary_provider = primary_provider,  identifier = attrs.get('parent_identifier')).first()

        l = db.query(SeasonLibrary).filter_by(type = type, identifier = attrs.get('identifier')).first()
        if not l:
            status = fireEvent('status.get', 'needs_update', single = True)
            l = SeasonLibrary(
                type = type,
                primary_provider = primary_provider,
                year = attrs.get('year'),
                identifier = attrs.get('identifier'),
                plot = toUnicode(attrs.get('plot')),
                tagline = toUnicode(attrs.get('tagline')),
                status_id = status.get('id'),
                info = {},
                parent = parent,
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
            handle('library.update.season', identifier = l.identifier, default_title = toUnicode(attrs.get('title', '')))

        library_dict = l.to_dict(self.default_dict)
        db.expire_all()
        return library_dict

    def update(self, identifier, default_title = '', force = False):

        if self.shuttingDown():
            return

        db = get_session()
        library = db.query(SeasonLibrary).filter_by(identifier = identifier).first()
        done_status = fireEvent('status.get', 'done', single = True)

        if library:
            library_dict = library.to_dict(self.default_dict)

        do_update = True

        parent_identifier =  None
        if library.parent is not None:
            parent_identifier =  library.parent.identifier

        if library.status_id == done_status.get('id') and not force:
            do_update = False

        season_params = {'season_identifier': identifier}
        info = fireEvent('season.info', merge = True, identifier = parent_identifier, params = season_params)

        # Don't need those here
        try: del info['in_wanted']
        except: pass
        try: del info['in_library']
        except: pass

        if not info or len(info) == 0:
            log.error('Could not update, no movie info to work with: %s', identifier)
            return False

        # Main info
        if do_update:
            library.plot = toUnicode(info.get('plot', ''))
            library.tagline = toUnicode(info.get('tagline', ''))
            library.year = info.get('year', 0)
            library.status_id = done_status.get('id')
            library.season_number = tryInt(info.get('seasonnumber', None))
            library.info.update(info)
            db.commit()

            # Titles
            [db.delete(title) for title in library.titles]
            db.commit()

            titles = info.get('titles', [])
            log.debug('Adding titles: %s', titles)
            counter = 0
            for title in titles:
                if not title:
                    continue
                title = toUnicode(title)
                t = LibraryTitle(
                    title = title,
                    simple_title = self.simplifyTitle(title),
                    # XXX: default was None; so added a quick hack since we don't really need titiles for seasons anyway
                    #default = (len(default_title) == 0 and counter == 0) or len(titles) == 1 or title.lower() == toUnicode(default_title.lower()) or (toUnicode(default_title) == u'' and toUnicode(titles[0]) == title)
                    default = True,
                )
                library.titles.append(t)
                counter += 1

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

        library_dict = library.to_dict(self.default_dict)
        db.expire_all()
        return library_dict

    def updateReleaseDate(self, identifier):
        '''XXX:  Not sure what this is for yet in relation to a tvshow'''
        pass
        #db = get_session()
        #library = db.query(SeasonLibrary).filter_by(identifier = identifier).first()

        #if not library.info:
            #library_dict = self.update(identifier, force = True)
            #dates = library_dict.get('info', {}).get('release_date')
        #else:
            #dates = library.info.get('release_date')

        #if dates and dates.get('expires', 0) < time.time() or not dates:
            #dates = fireEvent('movie.release_date', identifier = identifier, merge = True)
            #library.info.update({'release_date': dates })
            #db.commit()

        #db.expire_all()
        #return dates


    #TODO: Add to base class
    def simplifyTitle(self, title):

        title = toUnicode(title)

        nr_prefix = '' if title[0] in ascii_letters else '#'
        title = simplifyString(title)

        for prefix in ['the ']:
            if prefix == title[:len(prefix)]:
                title = title[len(prefix):]
                break

        return nr_prefix + title
