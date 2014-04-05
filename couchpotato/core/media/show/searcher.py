import time
from couchpotato import Env, get_db
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import getTitle, toIterable
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.base import SearcherBase
from couchpotato.core.media._base.searcher.main import SearchSetupError
from couchpotato.core.media.show import ShowTypeBase
from qcond import QueryCondenser

log = CPLog(__name__)

autoload = 'ShowSearcher'


class ShowSearcher(SearcherBase, ShowTypeBase):

    type = ['show', 'season', 'episode']

    in_progress = False

    def __init__(self):
        super(ShowSearcher, self).__init__()

        self.query_condenser = QueryCondenser()

        addEvent('season.searcher.single', self.singleSeason)
        addEvent('episode.searcher.single', self.singleEpisode)

        addEvent('searcher.correct_release', self.correctRelease)
        addEvent('searcher.get_search_title', self.getSearchTitle)



    def single(self, media, search_protocols = None, manual = False):

        # Find out search type
        try:
            if not search_protocols:
                search_protocols = fireEvent('searcher.protocols', single = True)
        except SearchSetupError:
            return

        if not media['profile_id'] or media['status'] == 'done':
            log.debug('Show doesn\'t have a profile or already done, assuming in manage tab.')
            return

        show_title = fireEvent('media.search_query', media, condense = False, single = True)

        fireEvent('notify.frontend', type = 'show.searcher.started.%s' % media['_id'], data = True, message = 'Searching for "%s"' % show_title)

        media = self.extendShow(media)

        db = get_db()

        profile = db.get('id', media['profile_id'])
        quality_order = fireEvent('quality.order', single = True)

        seasons = media.get('seasons', {})
        for sx in seasons:

            # Skip specials for now TODO: set status for specials to skipped by default
            if sx == 0: continue

            season = seasons.get(sx)

            # Check if full season can be downloaded TODO: add
            season_success = self.singleSeason(season, media, profile)

            # Do each episode seperately
            if not season_success:
                episodes = season.get('episodes', {})
                for ex in episodes:
                    episode = episodes.get(ex)

                    self.singleEpisode(episode, season, media, profile, quality_order, search_protocols)

                    # TODO
                    return

            # TODO
            return

        fireEvent('notify.frontend', type = 'show.searcher.ended.%s' % media['_id'], data = True)

    def singleSeason(self, media, show, profile):

        # Check if any episode is already snatched
        active = 0
        episodes = media.get('episodes', {})
        for ex in episodes:
            episode = episodes.get(ex)

            if episode.get('status') in ['active']:
                active += 1

        if active != len(episodes):
            return False

        # Try and search for full season
        # TODO:

        return False

    def singleEpisode(self, media, season, show, profile, quality_order, search_protocols = None, manual = False):


        # TODO: check episode status


        # TODO: check air date
        #if not self.conf('always_search') and not self.couldBeReleased(quality_type['quality']['identifier'] in pre_releases, release_dates, movie['library']['year']):
        #    too_early_to_search.append(quality_type['quality']['identifier'])
        #    return

        ret = False
        has_better_quality = None
        found_releases = []
        too_early_to_search = []

        releases = fireEvent('release.for_media', media['_id'], single = True)
        show_title = getTitle(show)
        episode_identifier = '%s S%02d%s' % (show_title, season['info'].get('number', 0), "E%02d" % media['info'].get('number'))

        # Add parents
        media['show'] = show
        media['season'] = season

        index = 0
        for q_identifier in profile.get('qualities'):
            quality_custom = {
                'quality': q_identifier,
                'finish': profile['finish'][index],
                'wait_for': profile['wait_for'][index],
                '3d': profile['3d'][index] if profile.get('3d') else False
            }

            has_better_quality = 0

            # See if better quality is available
            for release in releases:
                if quality_order.index(release['quality']) <= quality_order.index(q_identifier) and release['status'] not in ['available', 'ignored', 'failed']:
                    has_better_quality += 1

            # Don't search for quality lower then already available.
            if has_better_quality is 0:

                log.info('Searching for %s in %s', (episode_identifier, q_identifier))
                quality = fireEvent('quality.single', identifier = q_identifier, single = True)
                quality['custom'] = quality_custom

                results = fireEvent('searcher.search', search_protocols, media, quality, single = True)
                if len(results) == 0:
                    log.debug('Nothing found for %s in %s', (episode_identifier, q_identifier))

                # Add them to this movie releases list
                found_releases += fireEvent('release.create_from_search', results, media, quality, single = True)

                # Try find a valid result and download it
                if fireEvent('release.try_download_result', results, media, quality, manual, single = True):
                    ret = True

                # Remove releases that aren't found anymore
                for release in releases:
                    if release.get('status') == 'available' and release.get('identifier') not in found_releases:
                        fireEvent('release.delete', release.get('id'), single = True)
            else:
                log.info('Better quality (%s) already available or snatched for %s', (q_identifier, episode_identifier))
                fireEvent('media.restatus', media['_id'])
                break

            # Break if CP wants to shut down
            if self.shuttingDown() or ret:
                break

        if len(too_early_to_search) > 0:
            log.info2('Too early to search for %s, %s', (too_early_to_search, episode_identifier))

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

    def extendShow(self, media):

        db = get_db()

        seasons = db.get_many('media_children', media['_id'], with_doc = True)

        media['seasons'] = {}

        for sx in seasons:
            season = sx['doc']

            # Add episode info
            season['episodes'] = {}
            episodes = db.get_many('media_children', sx['_id'], with_doc = True)

            for se in episodes:
                episode = se['doc']
                season['episodes'][episode['info'].get('number')] = episode

            # Add season to show
            media['seasons'][season['info'].get('number', 0)] = season

        return media

    def searchAll(self):
        pass

    def getSearchTitle(self, media):
        # TODO: this should be done for season and episode
        if media['type'] == 'season':
            return getTitle(media)
        elif media['type'] == 'episode':
            return getTitle(media)
