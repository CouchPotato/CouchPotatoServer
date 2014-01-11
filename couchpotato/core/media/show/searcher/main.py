from couchpotato import Env, get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import getTitle, toIterable
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.main import SearchSetupError
from couchpotato.core.media.show._base import ShowBase
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Media
from qcond import QueryCondenser
from qcond.helpers import simplify

log = CPLog(__name__)


class ShowSearcher(Plugin):

    type = ['show', 'season', 'episode']

    in_progress = False

    def __init__(self):
        super(ShowSearcher, self).__init__()

        self.query_condenser = QueryCondenser()

        for type in toIterable(self.type):
            addEvent('%s.searcher.single' % type, self.single)

        addEvent('searcher.correct_release', self.correctRelease)

    def single(self, media, search_protocols = None, manual = False):
        show, season, episode = self.getLibraries(media['library'])

        db = get_session()

        if media['type'] == 'show':
            for library in season:
                # TODO ideally we shouldn't need to fetch the media for each season library here
                m = db.query(Media).filter_by(library_id = library['library_id']).first()

                fireEvent('season.searcher.single', m.to_dict(ShowBase.search_dict))

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

        #pre_releases = fireEvent('quality.pre_releases', single = True)

        found_releases = []
        too_early_to_search = []

        default_title = fireEvent('library.query', media['library'], condense = False, single=True)
        if not default_title:
            log.error('No proper info found for episode, removing it from library to cause it from having more issues.')
            #fireEvent('episode.delete', episode['id'], single = True)
            return

        if not show or not season:
            log.error('Unable to find show or season library in database, missing required data for searching')
            return

        fireEvent('notify.frontend', type = 'show.searcher.started.%s' % media['id'], data = True, message = 'Searching for "%s"' % default_title)

        ret = False
        has_better_quality = None

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

                log.info('Search for %s S%02d%s in %s', (
                    getTitle(show),
                    season['season_number'],
                    "E%02d" % episode['episode_number'] if episode and len(episode) == 1 else "",
                    quality_type['quality']['label'])
                )
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
                fireEvent('media.restatus', media['id'])
                break

            # Break if CP wants to shut down
            if self.shuttingDown() or ret:
                break

        if len(too_early_to_search) > 0:
            log.info2('Too early to search for %s, %s', (too_early_to_search, default_title))
        elif media['type'] == 'season' and not ret and has_better_quality is 0:
            # If nothing was found, start searching for episodes individually
            log.info('No season pack found, starting individual episode search')

            for library in episode:
                # TODO ideally we shouldn't need to fetch the media for each episode library here
                m = db.query(Media).filter_by(library_id = library['library_id']).first()

                fireEvent('episode.searcher.single', m.to_dict(ShowBase.search_dict))


        fireEvent('notify.frontend', type = 'show.searcher.ended.%s' % media['id'], data = True)

        return ret

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
        match = fireEvent('matcher.match', release, media, quality, single = True)
        if match:
            return match.weight

        return False

    def getLibraries(self, library):
        if 'related_libraries' not in library:
            log.warning("'related_libraries' missing from media library, unable to continue searching")
            return None, None, None

        libraries = library['related_libraries']

        # Show always collapses as there can never be any multiples
        show = libraries.get('show', [])
        show = show[0] if len(show) else None

        # Season collapses if the subject is a season or episode
        season = libraries.get('season', [])
        if library['type'] in ['season', 'episode']:
            season = season[0] if len(season) else None

        # Episode collapses if the subject is a episode
        episode = libraries.get('episode', [])
        if library['type'] == 'episode':
            episode = episode[0] if len(episode) else None

        return show, season, episode
