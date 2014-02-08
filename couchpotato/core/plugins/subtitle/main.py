from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode, sp
from couchpotato.core.helpers.variable import splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
import subliminal
import traceback

log = CPLog(__name__)


class Subtitle(Plugin):

    services = ['opensubtitles', 'thesubdb', 'subswiki', 'podnapisi']

    def __init__(self):
        addEvent('renamer.before', self.searchSingle)

    def searchSingle(self, group):
        if self.isDisabled(): return

        try:
            available_languages = sum(group['subtitle_language'].values(), [])
            downloaded = []
            files = [toUnicode(x) for x in group['files']['movie']]
            log.debug('Searching for subtitles for: %s', files)

            for lang in self.getLanguages():
                if lang not in available_languages:
                    download = subliminal.download_subtitles(files, multi = True, force = False, languages = [lang], services = self.services, cache_dir = Env.get('cache_dir'))
                    for subtitle in download:
                        downloaded.extend(download[subtitle])

            for d_sub in downloaded:
                log.info('Found subtitle (%s): %s', (d_sub.language.alpha2, files))
                group['files']['subtitle'].append(sp(d_sub.path))
                group['before_rename'].append(sp(d_sub.path))
                group['subtitle_language'][sp(d_sub.path)] = [d_sub.language.alpha2]

            return True

        except:
            log.error('Failed searching for subtitle: %s', (traceback.format_exc()))

        return False

    def getLanguages(self):
        return splitString(self.conf('languages'))
