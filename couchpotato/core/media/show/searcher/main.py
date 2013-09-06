from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.main import SearchSetupError
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Media

log = CPLog(__name__)


class ShowSearcher(Plugin):

    in_progress = False

    def __init__(self):
        super(ShowSearcher, self).__init__()

        addEvent('show.searcher.single', self.single)
        addEvent('searcher.get_search_title', self.getSearchTitle)

    def _lookupMedia(self, media):
        db = get_session()

        media_library = db.query(Media).filter_by(id = media['id']).first().library

        show = None
        season = None
        episode = None

        if media['type'] == 'episode':
            show = media_library.parent.parent
            season = media_library.parent
            episode = media_library

        if media['type'] == 'season':
            show = media_library.parent
            season = media_library

        if media['type'] == 'show':
            show = media_library

        return show, season, episode

    def single(self, media, search_protocols = None):
        if media['type'] == 'show':
            # TODO handle show searches (scan all seasons)
            return

        # Find out search type
        try:
            if not search_protocols:
                search_protocols = fireEvent('searcher.protocols', single = True)
        except SearchSetupError:
            return

        done_status = fireEvent('status.get', 'done', single = True)

        if not media['profile'] or media['status_id'] == done_status.get('id'):
            log.debug('Episode doesn\'t have a profile or already done, assuming in manage tab.')
            return

        db = get_session()

        pre_releases = fireEvent('quality.pre_releases', single = True)
        available_status, ignored_status, failed_status = fireEvent('status.get', ['available', 'ignored', 'failed'], single = True)

        found_releases = []
        too_early_to_search = []

        default_title = getTitle(media['library'])
        if not default_title:
            log.error('No proper info found for episode, removing it from library to cause it from having more issues.')
            #fireEvent('episode.delete', episode['id'], single = True)
            return

        show, season, episode = self._lookupMedia(media)
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

                log.info('Search for %s S%02d%s in %s', (getTitle(show), season.season_number, "E%02d" % episode.episode_number if episode else "", quality_type['quality']['label']))
                quality = fireEvent('quality.single', identifier = quality_type['quality']['identifier'], single = True)

                results = []
                for search_protocol in search_protocols:
                    protocol_results = fireEvent('provider.search.%s.%s' % (search_protocol, media['type']), media, quality, merge = True)
                    if protocol_results:
                        results += protocol_results

                log.info('%d results found' % len(results))

    def getSearchTitle(self, media):
        show, season, episode = self._lookupMedia(media)
        if show is None:
            return None

        name = ''
        if season is not None:
            name = ' S%02d' % season.season_number

            if episode is not None:
                name += 'E%02d' % episode.episode_number

        show_title = getTitle(show)
        if not show_title:
            return None

        return show_title + name
