from couchpotato.core.logger import CPLog
from couchpotato.core.providers.subtitle.base import SubtitleProvider
from couchpotato.environment import Env
from libs import subliminal

log = CPLog(__name__)


class SubliminalProvider(SubtitleProvider):

    plugins = ['OpenSubtitles', 'TheSubDB', 'SubsWiki']

    def search(self, files = [], languages = []):

        # download subtitles
        with subliminal.Subliminal(cache_dir = Env.get('cache_dir'), multi = True,
                                   languages = self.getLanguages(), plugins = self.plugins) as subli:
            subtitles = subli.downloadSubtitles(files)

        print subtitles

        return subtitles
