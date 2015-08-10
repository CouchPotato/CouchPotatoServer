import time

from couchpotato import fireEvent, get_db, Env
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEventAsync
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.main import Searcher
from couchpotato.core.media._base.searcher.main import SearchSetupError
from couchpotato.core.media.show import ShowTypeBase
from couchpotato.core.helpers.variable import strtotime

log = CPLog(__name__)

autoload = 'EpisodeSearcher'


class EpisodeSearcher(Searcher, ShowTypeBase):
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

    def correctRelease(self, release = None, media = None, quality = None, **kwargs):
        if media.get('type') != 'show.episode': return

        retention = Env.setting('retention', section = 'nzb')

        if release.get('seeders') is None and 0 < retention < release.get('age', 0):
            log.info2('Wrong: Outside retention, age is %s, needs %s or lower: %s', (release['age'], retention, release['name']))
            return False

        # Check for required and ignored words
        if not self.correctWords(release['name'], media):
            return False

        preferred_quality = quality if quality else fireEvent('quality.single', identifier = quality['identifier'], single = True)

        # Contains lower quality string
        contains_other = self.containsOtherQuality(release, preferred_quality = preferred_quality, types= [self._type])
        if contains_other != False:
            log.info2('Wrong: %s, looking for %s, found %s', (release['name'], quality['label'], [x for x in contains_other] if contains_other else 'no quality'))
            return False

        # TODO Matching is quite costly, maybe we should be caching release matches somehow? (also look at caper optimizations)
        match = fireEvent('matcher.match', release, media, quality, single = True)
        if match:
            return match.weight

        return False

    def couldBeReleased(self, is_pre_release, dates, media):
        """
        Determine if episode could have aired by now

        @param is_pre_release: True if quality is pre-release, otherwise False. Ignored for episodes.
        @param dates:
        @param media: media dictionary to retrieve episode air date from.
        @return: dict, with media
        """
        now = time.time()
        released = strtotime(media.get('info', {}).get('released'), '%Y-%m-%d')

        if (released < now):
            return True

        return False

    def getProfileId(self, media):
        assert media and media['type'] == 'show.episode'

        profile_id = None

        related = fireEvent('library.related', media, single = True)
        if related:
            show = related.get('show')
            if show:
                profile_id = show.get('profile_id')

        return profile_id
