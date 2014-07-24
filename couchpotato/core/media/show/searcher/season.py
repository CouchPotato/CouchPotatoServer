from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.base import SearcherBase
from couchpotato.core.media.show import ShowTypeBase

log = CPLog(__name__)

autoload = 'SeasonSearcher'


class SeasonSearcher(SearcherBase, ShowTypeBase):
    type = 'season'

    in_progress = False

    def __init__(self):
        super(SeasonSearcher, self).__init__()

        addEvent('%s.searcher.single' % self.getType(), self.single)

    def single(self, media, show, profile):

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
