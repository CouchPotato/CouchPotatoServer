from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent, fireEventAsync
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.main import Searcher
from couchpotato.core.media._base.searcher.main import SearchSetupError
from couchpotato.core.media.show import ShowTypeBase

log = CPLog(__name__)

autoload = 'ShowSearcher'


class ShowSearcher(Searcher, ShowTypeBase):
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

    def single(self, media, search_protocols = None, manual = False, force_download = False, notify = True):

        db = get_db()
        profile = db.get('id', media['profile_id'])

        if not profile or (media['status'] == 'done' and not manual):
            log.debug('Media does not have a profile or already done, assuming in manage tab.')
            fireEvent('media.restatus', media['_id'], single = True)
            return

        default_title = getTitle(media)
        if not default_title:
            log.error('No proper info found for media, removing it from library to stop it from causing more issues.')
            fireEvent('media.delete', media['_id'], single = True)
            return

        fireEvent('notify.frontend', type = 'show.searcher.started.%s' % media['_id'], data = True, message = 'Searching for "%s"' % default_title)

        seasons = []

        tree = fireEvent('library.tree', media, single = True)
        if tree:
            for season in tree.get('seasons', []):
                if season.get('info'):
                    continue

                # Skip specials (and seasons missing 'number') for now
                # TODO: set status for specials to skipped by default
                if not season['info'].get('number'):
                    continue

                seasons.append(season)

        result = True
        for season in seasons:
            if not fireEvent('show.season.searcher.single', search_protocols, manual, force_download, False):
                result = False
                break

        fireEvent('notify.frontend', type = 'show.searcher.ended.%s' % media['_id'], data = True)

        return result

    def getSearchTitle(self, media):
        show = None
        if media.get('type') == 'show':
            show = media
        elif media.get('type') in ('show.season', 'show.episode'):
            related = fireEvent('library.related', media, single = True)
            show = related['show']

        if show:
            return getTitle(show)
