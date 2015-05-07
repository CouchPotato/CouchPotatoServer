from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent, fireEventAsync
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

        addEvent('%s.searcher.all' % self.getType(), self.searchAll)
        addEvent('%s.searcher.single' % self.getType(), self.single)
        addEvent('searcher.get_search_title', self.getSearchTitle)

        addApiView('%s.searcher.full_search' % self.getType(), self.searchAllView, docs = {
            'desc': 'Starts a full search for all wanted episodes',
        })

    def searchAllView(self, **kwargs):
        fireEventAsync('%s.searcher.all' % self.getType(), manual = True)

        return {
            'success': not self.in_progress
        }

    def searchAll(self, manual = False):
        pass

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

        show_tree = fireEvent('library.tree', media, single = True)

        db = get_db()

        profile = db.get('id', media['profile_id'])
        quality_order = fireEvent('quality.order', single = True)

        for season in show_tree.get('seasons', []):
            if not season.get('info'):
                continue

            # Skip specials (and seasons missing 'number') for now
            # TODO: set status for specials to skipped by default
            if not season['info'].get('number'):
                continue

            # Check if full season can be downloaded
            fireEvent('show.season.searcher.single', season, profile, quality_order, search_protocols, manual)

            # TODO (testing) only snatch one season
            return

        fireEvent('notify.frontend', type = 'show.searcher.ended.%s' % media['_id'], data = True)

    def getSearchTitle(self, media):
        if media.get('type') != 'show':
            related = fireEvent('library.related', media, single = True)
            show = related['show']
        else:
            show = media

        return getTitle(show)
