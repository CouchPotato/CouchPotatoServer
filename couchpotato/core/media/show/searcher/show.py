from couchpotato import get_db
from couchpotato.core.event import fireEvent, addEvent
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.base import SearcherBase
from couchpotato.core.media._base.searcher.main import SearchSetupError
from couchpotato.core.media.show import ShowTypeBase

log = CPLog(__name__)

autoload = 'ShowSearcher'


class ShowSearcher(SearcherBase, ShowTypeBase):
    type = 'show'

    in_progress = False

    def __init__(self):
        super(ShowSearcher, self).__init__()

        addEvent('%s.searcher.single' % self.getType(), self.single)

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
            season_success = fireEvent('show.season.searcher.single', season, media, profile)

            # Do each episode seperately
            if not season_success:
                episodes = season.get('episodes', {})
                for ex in episodes:
                    episode = episodes.get(ex)

                    fireEvent('show.episode.searcher.single', episode, season, media, profile, quality_order, search_protocols)

                    # TODO
                    return

            # TODO
            return

        fireEvent('notify.frontend', type = 'show.searcher.ended.%s' % media['_id'], data = True)

    def getSearchTitle(self, media):
        if media.get('type') != 'show':
            related = fireEvent('library.related', media, single = True)
            show = related['show']
        else:
            show = media

        return getTitle(show)
