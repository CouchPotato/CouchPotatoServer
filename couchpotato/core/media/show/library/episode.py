import time
import traceback

from couchpotato import get_db
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.library.base import LibraryBase
from couchpotato.core.helpers.variable import tryInt


log = CPLog(__name__)

autload = 'EpisodeLibraryPlugin'


class EpisodeLibraryPlugin(LibraryBase):

    default_dict = {'titles': {}, 'files':{}}

    def __init__(self):
        addEvent('library.query', self.query)
        addEvent('library.identifier', self.identifier)
        addEvent('library.update.episode', self.update)

    def query(self, library, first = True, condense = True, include_identifier = True, **kwargs):
        if library is list or library.get('type') != 'episode':
            return

        # Get the titles of the season
        if not library.get('related_libraries', {}).get('season', []):
            log.warning('Invalid library, unable to determine title.')
            return

        titles = fireEvent(
            'library.query',
            library['related_libraries']['season'][0],
            first=False,
            include_identifier=include_identifier,
            condense=condense,

            single=True
        )

        identifier = fireEvent('library.identifier', library, single = True)

        # Add episode identifier to titles
        if include_identifier and identifier.get('episode'):
            titles = [title + ('E%02d' % identifier['episode']) for title in titles]


        if first:
            return titles[0] if titles else None

        return titles


    def identifier(self, library):
        if library.get('type') != 'episode':
            return

        identifier = {
            'season': None,
            'episode': None
        }

        scene_map = library['info'].get('map_episode', {}).get('scene')

        if scene_map:
            # Use scene mappings if they are available
            identifier['season'] = scene_map.get('season')
            identifier['episode'] = scene_map.get('episode')
        else:
            # Fallback to normal season/episode numbers
            identifier['season'] = library.get('season_number')
            identifier['episode'] = library.get('episode_number')


        # Cast identifiers to integers
        # TODO this will need changing to support identifiers with trailing 'a', 'b' characters
        identifier['season'] = tryInt(identifier['season'], None)
        identifier['episode'] = tryInt(identifier['episode'], None)

        return identifier

    def update(self, media_id = None, identifier = None, default_title = '', force = False):

        if self.shuttingDown():
            return

        db = get_db()

        if media_id:
            media = db.get('id', media_id)
        else:
            media = db.get('media', identifier, with_doc = True)['doc']

        do_update = True

        if media.get('status') == 'done' and not force:
            do_update = False

        episode_params = {
            'season_identifier': media.get('parent'),
            'episode_identifier': media.get('identifier'),
            'episode': media.get('episode_number'),
            'absolute': media.get('episode_number'),
        }
        info = fireEvent('episode.info', merge = True, params = episode_params)

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
            episode = {
                'plot': toUnicode(info.get('plot', '')),
                'tagline': toUnicode(info.get('tagline', '')),
                'year': info.get('year', 0),
                'status_id': 'done',
                'season_number': tryInt(info.get('seasonnumber', None)),
                'episode_number': tryInt(info.get('episodenumber', None)),
                'absolute_number': tryInt(info.get('absolute_number', None)),
                'last_updated': tryInt(info.get('lastupdated', time.time())),
            }

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
                    default = (len(default_title) == 0 and counter == 0) or len(titles) == 1 or title.lower() == toUnicode(default_title.lower()) or (toUnicode(default_title) == u'' and toUnicode(titles[0]) == title)
                )
                library.titles.append(t)
                counter += 1

            media.update(episode)
            db.update(media)

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
