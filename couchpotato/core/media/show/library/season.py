import traceback

from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.library.base import LibraryBase
from couchpotato.core.helpers.variable import tryInt


log = CPLog(__name__)

autload = 'SeasonLibraryPlugin'


class SeasonLibraryPlugin(LibraryBase):

    def __init__(self):
        addEvent('library.query', self.query)
        addEvent('library.identifier', self.identifier)
        addEvent('library.update.season', self.update)

    def query(self, library, first = True, condense = True, include_identifier = True, **kwargs):
        if library is list or library.get('type') != 'season':
            return

        # Get the titles of the show
        if not library.get('related_libraries', {}).get('show', []):
            log.warning('Invalid library, unable to determine title.')
            return

        titles = fireEvent(
            'library.query',
            library['related_libraries']['show'][0],
            first=False,
            condense=condense,

            single=True
        )

        # Add season map_names if they exist
        if 'map_names' in library['info']:
            season_names = library['info']['map_names'].get(str(library['season_number']), {})

            # Add titles from all locations
            # TODO only add name maps from a specific location
            for location, names in season_names.items():
                titles += [name for name in names if name and name not in titles]


        identifier = fireEvent('library.identifier', library, single = True)

        # Add season identifier to titles
        if include_identifier and identifier.get('season') is not None:
            titles = [title + (' S%02d' % identifier['season']) for title in titles]


        if first:
            return titles[0] if titles else None

        return titles

    def identifier(self, library):
        if library.get('type') != 'season':
            return

        return {
            'season': tryInt(library['season_number'], None)
        }

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
