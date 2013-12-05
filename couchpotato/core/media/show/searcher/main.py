from couchpotato import Env, get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import getTitle, tryInt, toIterable
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.main import SearchSetupError
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Media
from qcond import QueryCondenser
from qcond.helpers import simplify

log = CPLog(__name__)


class ShowSearcher(Plugin):

    type = ['show', 'season', 'episode']

    in_progress = False

    # TODO come back to this later, think this could be handled better
    quality_map = {
        'webdl_1080p': {'resolution': ['1080p'], 'source': ['webdl', ['web', 'dl']]},
        'webdl_720p': {'resolution': ['720p'], 'source': ['webdl', ['web', 'dl']]},

        'hdtv_720p': {'resolution': ['720p'], 'source': ['hdtv']},
        'hdtv_sd': {'resolution': ['480p', None], 'source': ['hdtv']},
    }

    def __init__(self):
        super(ShowSearcher, self).__init__()

        self.query_condenser = QueryCondenser()

        for type in toIterable(self.type):
            addEvent('%s.searcher.single' % type, self.single)

        addEvent('searcher.get_search_title', self.getSearchTitle)

        addEvent('searcher.correct_match', self.correctMatch)
        addEvent('searcher.correct_release', self.correctRelease)

    def single(self, media, search_protocols = None, manual = False):
        show, season, episode = self.getLibraries(media['library'])

        if media['type'] == 'show':
            # TODO handle show searches (scan all seasons)
            return

        # Find out search type
        try:
            if not search_protocols:
                search_protocols = fireEvent('searcher.protocols', single = True)
        except SearchSetupError:
            return

        done_status, available_status, ignored_status, failed_status = fireEvent('status.get', ['done', 'available', 'ignored', 'failed'], single = True)

        if not media['profile'] or media['status_id'] == done_status.get('id'):
            log.debug('Episode doesn\'t have a profile or already done, assuming in manage tab.')
            return

        db = get_session()

        #pre_releases = fireEvent('quality.pre_releases', single = True)

        found_releases = []
        too_early_to_search = []

        default_title = self.getSearchTitle(media)
        if not default_title:
            log.error('No proper info found for episode, removing it from library to cause it from having more issues.')
            #fireEvent('episode.delete', episode['id'], single = True)
            return

        if not show or not season:
            log.error('Unable to find show or season library in database, missing required data for searching')
            return

        fireEvent('notify.frontend', type = 'show.searcher.started.%s' % media['id'], data = True, message = 'Searching for "%s"' % default_title)

        ret = False
        for quality_type in media['profile']['types']:
            # TODO check air date?
            #if not self.conf('always_search') and not self.couldBeReleased(quality_type['quality']['identifier'] in pre_releases, release_dates, movie['library']['year']):
            #    too_early_to_search.append(quality_type['quality']['identifier'])
            #    continue

            has_better_quality = 0

            # See if better quality is available
            for release in media['releases']:
                if release['quality']['order'] <= quality_type['quality']['order'] and release['status_id'] not in [available_status.get('id'), ignored_status.get('id'), failed_status.get('id')]:
                    has_better_quality += 1

            # Don't search for quality lower then already available.
            if has_better_quality is 0:

                log.info('Search for %s S%02d%s in %s', (getTitle(show), season['season_number'], "E%02d" % episode['episode_number'] if episode else "", quality_type['quality']['label']))
                quality = fireEvent('quality.single', identifier = quality_type['quality']['identifier'], single = True)

                results = fireEvent('searcher.search', search_protocols, media, quality, single = True)
                if len(results) == 0:
                    log.debug('Nothing found for %s in %s', (default_title, quality_type['quality']['label']))

                # Check if movie isn't deleted while searching
                if not db.query(Media).filter_by(id = media.get('id')).first():
                    break

                # Add them to this movie releases list
                found_releases += fireEvent('release.create_from_search', results, media, quality_type, single = True)

                # Try find a valid result and download it
                if fireEvent('release.try_download_result', results, media, quality_type, manual, single = True):
                    ret = True

                # Remove releases that aren't found anymore
                for release in media.get('releases', []):
                    if release.get('status_id') == available_status.get('id') and release.get('identifier') not in found_releases:
                        fireEvent('release.delete', release.get('id'), single = True)
            else:
                log.info('Better quality (%s) already available or snatched for %s', (quality_type['quality']['label'], default_title))
                fireEvent('movie.restatus', media['id'])
                break

            # Break if CP wants to shut down
            if self.shuttingDown() or ret:
                break

        if len(too_early_to_search) > 0:
            log.info2('Too early to search for %s, %s', (too_early_to_search, default_title))

        fireEvent('notify.frontend', type = 'show.searcher.ended.%s' % media['id'], data = True)

        return ret

    def getSearchTitle(self, media):
        if media['type'] not in ['show', 'season', 'episode']:
            return

        show, season, episode = self.getLibraries(media['library'])

        if not show:
            return None

        titles = []

        # Add season map_names if they exist
        if season is not None and 'map_names' in show['info']:
            season_names = show['info']['map_names'].get(str(season['season_number']), {})

            # Add titles from all locations
            # TODO only add name maps from a specific location
            for location, names in season_names.items():
                titles += [name for name in names if name not in titles]

        # Add show titles
        titles += [title['title'] for title in show['titles'] if title['title'] not in titles]

        # Use QueryCondenser to build a list of optimal search titles
        condensed_titles = self.query_condenser.distinct(titles)

        title = None

        # TODO try other titles if searching doesn't return results

        if len(condensed_titles):
            # Return the first condensed title if one exists
            title = condensed_titles[0]
        elif len(titles):
            # Fallback to first raw title
            title = simplify(titles[0])
        else:
            return None

        # Add the identifier to search title
        identifier = fireEvent('library.identifier', media['library'], single = True)

        # TODO this needs to support other identifier formats
        if identifier['season']:
            title += ' S%02d' % identifier['season']

            if identifier['episode']:
                title += 'E%02d' % identifier['episode']

        return title

    def correctRelease(self, release = None, media = None, quality = None, **kwargs):

        if media.get('type') not in ['season', 'episode']: return

        retention = Env.setting('retention', section = 'nzb')

        if release.get('seeders') is None and 0 < retention < release.get('age', 0):
            log.info2('Wrong: Outside retention, age is %s, needs %s or lower: %s', (release['age'], retention, release['name']))
            return False

        # Check for required and ignored words
        if not fireEvent('searcher.correct_words', release['name'], media, single = True):
            return False

        # TODO Matching is quite costly, maybe we should be caching release matches somehow? (also look at caper optimizations)
        match = fireEvent('matcher.best', release, media, quality, single = True)
        if match:
            return match.weight

        return False

    def correctMatch(self, chain, release, media, quality):
        log.info("Checking if '%s' is valid", release['name'])
        log.info2('Release parsed as: %s', chain.info)

        if not fireEvent('matcher.correct_quality', chain, quality, self.quality_map, single = True):
            log.info('Wrong: %s, quality does not match', release['name'])
            return False

        if not fireEvent('matcher.correct_identifier', chain, media):
            log.info('Wrong: %s, identifier does not match', release['name'])
            return False

        if not fireEvent('matcher.correct_title', chain, media):
            log.info("Wrong: '%s', undetermined naming.", (' '.join(chain.info['show_name'])))
            return False

        return True

    def getLibraries(self, library):
        if 'related_libraries' not in library:
            log.warning("'related_libraries' missing from media library, unable to continue searching")
            return None, None, None

        libraries = library['related_libraries']

        # Get libraries and return lists only if there is multiple items
        show = libraries.get('show', [])
        if len(show) <= 1:
            show = show[0] if len(show) else None

        season = libraries.get('season', [])
        if len(season) <= 1:
            season = season[0] if len(season) else None

        episode = libraries.get('episode', [])
        if len(episode) <= 1:
            episode = episode[0] if len(episode) else None

        return show, season, episode
