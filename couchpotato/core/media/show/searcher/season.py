from couchpotato import get_db, Env
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEventAsync, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.main import Searcher
from couchpotato.core.media.movie.searcher import SearchSetupError
from couchpotato.core.media.show import ShowTypeBase
from couchpotato.core.helpers.variable import getTitle

log = CPLog(__name__)

autoload = 'SeasonSearcher'


class SeasonSearcher(Searcher, ShowTypeBase):
    type = 'season'

    in_progress = False

    def __init__(self):
        super(SeasonSearcher, self).__init__()

        addEvent('%s.searcher.all' % self.getType(), self.searchAll)
        addEvent('%s.searcher.single' % self.getType(), self.single)
        addEvent('searcher.correct_release', self.correctRelease)

        addApiView('%s.searcher.full_search' % self.getType(), self.searchAllView, docs = {
            'desc': 'Starts a full search for all wanted seasons',
        })

    def searchAllView(self, **kwargs):
        fireEventAsync('%s.searcher.all' % self.getType(), manual = True)

        return {
            'success': not self.in_progress
        }

    def searchAll(self, manual = False):
        pass

    def single(self, media, search_protocols = None, manual = False, force_download = False, notify = True):

        # The user can prefer episode releases over season releases.
        prefer_episode_releases = self.conf('prefer_episode_releases')

        episodes = []
        all_episodes_available = self.couldBeReleased(False, [], media)

        event_type = 'show.season.searcher.started'
        related = fireEvent('library.related', media, single = True)
        default_title = getTitle(related.get('show'))
        fireEvent('notify.frontend', type = event_type, data = {'_id': media['_id']}, message = 'Searching for "%s"' % default_title)

        result = False
        if not all_episodes_available or prefer_episode_releases:
            result = True
            for episode in episodes:
                if not fireEvent('show.episode.searcher.single', episode, search_protocols, manual, force_download, False):
                    result = False
                    break

        if not result and all_episodes_available:
            # The user might have preferred episode releases over season
            # releases, but that did not work out, fallback to season releases.
            result = super(SeasonSearcher, self).single(media, search_protocols, manual, force_download, False)

        event_type = 'show.season.searcher.ended'
        fireEvent('notify.frontend', type = event_type, data = {'_id': media['_id']})

        return result

    def correctRelease(self, release = None, media = None, quality = None, **kwargs):
        if media.get('type') != 'show.season':
            return

        retention = Env.setting('retention', section = 'nzb')

        if release.get('seeders') is None and 0 < retention < release.get('age', 0):
            log.info2('Wrong: Outside retention, age is %s, needs %s or lower: %s', (release['age'], retention, release['name']))
            return False

        # Check for required and ignored words
        if not self.correctWords(release['name'], media):
            return False

        preferred_quality = quality if quality else fireEvent('quality.single', identifier = quality['identifier'], single = True)

        # Contains lower quality string
        contains_other = self.containsOtherQuality(release, preferred_quality = preferred_quality, types = [self._type])
        if contains_other != False:
            log.info2('Wrong: %s, looking for %s, found %s', (release['name'], quality['label'], [x for x in contains_other] if contains_other else 'no quality'))
            return False

        # TODO Matching is quite costly, maybe we should be caching release matches somehow? (also look at caper optimizations)
        match = fireEvent('matcher.match', release, media, quality, single = True)
        if match:
            return match.weight

        return False

    def couldBeReleased(self, is_pre_release, dates, media):
        episodes = []
        all_episodes_available = True

        related = fireEvent('library.related', media, single = True)
        if related:
            for episode in related.get('episodes', []):
                if episode.get('status') == 'active':
                    episodes.append(episode)
                else:
                    all_episodes_available = False
        if not episodes:
            all_episodes_available = False

        return all_episodes_available

    def getTitle(self, media):
        # FIXME: Season media type should have a title.
        #        e.g. <Show> Season <Number>
        title = None
        related = fireEvent('library.related', media, single = True)
        if related:
            title = getTitle(related.get('show'))
        return title

    def getProfileId(self, media):
        assert media and media['type'] == 'show.season'

        profile_id = None

        related = fireEvent('library.related', media, single = True)
        if related:
            show = related.get('show')
            if show:
                profile_id = show.get('profile_id')

        return profile_id
