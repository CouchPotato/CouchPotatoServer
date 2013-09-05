from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.main import SearchSetupError
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class ShowSearcher(Plugin):

    in_progress = False

    def __init__(self):
        super(ShowSearcher, self).__init__()

        addEvent('show.searcher.show', self.show)
        addEvent('show.searcher.season', self.season)
        addEvent('show.searcher.episode', self.episode)

    def _get_search_protocols(self):
        try:
            return fireEvent('searcher.protocols', single = True)
        except SearchSetupError:
            return None

    def show(self, show, search_protocols = None):
        # TODO - handover to searching for seasons
        pass

    def season(self, season, search_protocols = None):
        # Find out search type
        search_protocols = self._get_search_protocols() if not search_protocols else None
        if search_protocols is None:
            return

        done_status = fireEvent('status.get', 'done', single = True)

        if not season['profile'] or season['status_id'] == done_status.get('id'):
            log.debug('Season doesn\'t have a profile or already done, assuming in manage tab.')
            return

        db = get_session()

        pre_releases = fireEvent('quality.pre_releases', single = True)
        available_status, ignored_status, failed_status = fireEvent('status.get', ['available', 'ignored', 'failed'], single = True)

        found_releases = []
        too_early_to_search = []

        default_title = getTitle(season['library'])
        if not default_title:
            log.error('No proper info found for season, removing it from library to cause it from having more issues.')
            #fireEvent('season.delete', season['id'], single = True)
            return

        fireEvent('notify.frontend', type = 'show.searcher.started.%s' % season['id'], data = True, message = 'Searching for "%s"' % default_title)


    def episode(self, episode, search_protocols = None):
        # Find out search type
        search_protocols = self._get_search_protocols() if not search_protocols else None
        if search_protocols is None:
            return

        done_status = fireEvent('status.get', 'done', single = True)

        if not episode['profile'] or episode['status_id'] == done_status.get('id'):
            log.debug('Episode doesn\'t have a profile or already done, assuming in manage tab.')
            return

        db = get_session()

        pre_releases = fireEvent('quality.pre_releases', single = True)
        available_status, ignored_status, failed_status = fireEvent('status.get', ['available', 'ignored', 'failed'], single = True)

        found_releases = []
        too_early_to_search = []

        default_title = getTitle(episode['library'])
        if not default_title:
            log.error('No proper info found for episode, removing it from library to cause it from having more issues.')
            #fireEvent('episode.delete', episode['id'], single = True)
            return

        fireEvent('notify.frontend', type = 'show.searcher.started.%s' % episode['id'], data = True, message = 'Searching for "%s"' % default_title)
