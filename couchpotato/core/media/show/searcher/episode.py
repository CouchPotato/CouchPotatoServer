from couchpotato import fireEvent, get_db, Env
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEventAsync
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.base import SearcherBase
from couchpotato.core.media._base.searcher.main import SearchSetupError
from couchpotato.core.media.show import ShowTypeBase

log = CPLog(__name__)

autoload = 'EpisodeSearcher'


class EpisodeSearcher(SearcherBase, ShowTypeBase):
    type = 'episode'

    in_progress = False

    def __init__(self):
        super(EpisodeSearcher, self).__init__()

        addEvent('%s.searcher.all' % self.getType(), self.searchAll)
        addEvent('%s.searcher.single' % self.getType(), self.single)
        addEvent('searcher.correct_release', self.correctRelease)

        addApiView('%s.searcher.full_search' % self.getType(), self.searchAllView, docs = {
            'desc': 'Starts a full search for all wanted shows',
        })

        addApiView('%s.searcher.single' % self.getType(), self.singleView)

    def searchAllView(self, **kwargs):
        fireEventAsync('%s.searcher.all' % self.getType(), manual = True)

        return {
            'success': not self.in_progress
        }

    def searchAll(self, manual = False):
        pass

    def singleView(self, media_id, **kwargs):
        db = get_db()
        media = db.get('id', media_id)

        return {
            'result': fireEvent('%s.searcher.single' % self.getType(), media, single = True)
        }

    def single(self, media, profile = None, quality_order = None, search_protocols = None, manual = False):
        db = get_db()

        related = fireEvent('library.related', media, single = True)

        # TODO search_protocols, profile, quality_order can be moved to a base method
        # Find out search type
        try:
            if not search_protocols:
                search_protocols = fireEvent('searcher.protocols', single = True)
        except SearchSetupError:
            return

        if not profile and related['show']['profile_id']:
            profile = db.get('id', related['show']['profile_id'])

        if not quality_order:
            quality_order = fireEvent('quality.order', single = True)

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
        query = fireEvent('library.query', media, condense = False, single = True)

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

                log.info('Searching for %s in %s', (query, q_identifier))
                quality = fireEvent('quality.single', identifier = q_identifier, single = True)
                quality['custom'] = quality_custom

                results = fireEvent('searcher.search', search_protocols, media, quality, single = True)
                if len(results) == 0:
                    log.debug('Nothing found for %s in %s', (query, q_identifier))

                # Add them to this movie releases list
                found_releases += fireEvent('release.create_from_search', results, media, quality, single = True)

                # Try find a valid result and download it
                if fireEvent('release.try_download_result', results, media, quality, single = True):
                    ret = True

                # Remove releases that aren't found anymore
                for release in releases:
                    if release.get('status') == 'available' and release.get('identifier') not in found_releases:
                        fireEvent('release.delete', release.get('_id'), single = True)
            else:
                log.info('Better quality (%s) already available or snatched for %s', (q_identifier, query))
                fireEvent('media.restatus', media['_id'])
                break

            # Break if CP wants to shut down
            if self.shuttingDown() or ret:
                break

        if len(too_early_to_search) > 0:
            log.info2('Too early to search for %s, %s', (too_early_to_search, query))

    def correctRelease(self, release = None, media = None, quality = None, **kwargs):
        if media.get('type') != 'show.episode':
            return

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
