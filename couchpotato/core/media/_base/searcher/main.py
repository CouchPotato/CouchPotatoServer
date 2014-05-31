import datetime
import re

from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.variable import splitString, removeEmpty, removeDuplicate
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.base import SearcherBase


log = CPLog(__name__)


class Searcher(SearcherBase):

    # noinspection PyMissingConstructor
    def __init__(self):
        addEvent('searcher.protocols', self.getSearchProtocols)
        addEvent('searcher.contains_other_quality', self.containsOtherQuality)
        addEvent('searcher.correct_3d', self.correct3D)
        addEvent('searcher.correct_year', self.correctYear)
        addEvent('searcher.correct_name', self.correctName)
        addEvent('searcher.correct_words', self.correctWords)
        addEvent('searcher.search', self.search)

        addApiView('searcher.full_search', self.searchAllView, docs = {
            'desc': 'Starts a full search for all media',
        })

        addApiView('searcher.progress', self.getProgressForAll, docs = {
            'desc': 'Get the progress of all media searches',
            'return': {'type': 'object', 'example': """{
    'movie': False || object, total & to_go,
    'show': False || object, total & to_go,
}"""},
        })

    def searchAllView(self):

        results = {}
        for _type in fireEvent('media.types'):
            results[_type] = fireEvent('%s.searcher.all_view' % _type)

        return results

    def getProgressForAll(self):
        progress = fireEvent('searcher.progress', merge = True)
        return progress

    def search(self, protocols, media, quality):
        results = []

        for search_protocol in protocols:
            protocol_results = fireEvent('provider.search.%s.%s' % (search_protocol, media.get('type')), media, quality, merge = True)
            if protocol_results:
                results += protocol_results

        sorted_results = sorted(results, key = lambda k: k['score'], reverse = True)

        download_preference = self.conf('preferred_method', section = 'searcher')
        if download_preference != 'both':
            sorted_results = sorted(sorted_results, key = lambda k: k['protocol'][:3], reverse = (download_preference == 'torrent'))

        return sorted_results

    def getSearchProtocols(self):

        download_protocols = fireEvent('download.enabled_protocols', merge = True)
        provider_protocols = fireEvent('provider.enabled_protocols', merge = True)

        if download_protocols and len(list(set(provider_protocols) & set(download_protocols))) == 0:
            log.error('There aren\'t any providers enabled for your downloader (%s). Check your settings.', ','.join(download_protocols))
            return []

        for useless_provider in list(set(provider_protocols) - set(download_protocols)):
            log.debug('Provider for "%s" enabled, but no downloader.', useless_provider)

        search_protocols = download_protocols

        if len(search_protocols) == 0:
            log.error('There aren\'t any downloaders enabled. Please pick one in settings.')
            return []

        return search_protocols

    def containsOtherQuality(self, nzb, movie_year = None, preferred_quality = None):
        if not preferred_quality: preferred_quality = {}

        found = {}

        # Try guessing via quality tags
        guess = fireEvent('quality.guess', files = [nzb.get('name')], size = nzb.get('size', None), single = True)
        if guess:
            found[guess['identifier']] = True

        # Hack for older movies that don't contain quality tag
        name = nzb['name']
        size = nzb.get('size', 0)

        year_name = fireEvent('scanner.name_year', name, single = True)
        if len(found) == 0 and movie_year < datetime.datetime.now().year - 3 and not year_name.get('year', None):
            if size > 20000:  # Assume bd50
                log.info('Quality was missing in name, assuming it\'s a BR-Disk based on the size: %s', size)
                found['bd50'] = True
            elif size > 3000:  # Assume dvdr
                log.info('Quality was missing in name, assuming it\'s a DVD-R based on the size: %s', size)
                found['dvdr'] = True
            else:  # Assume dvdrip
                log.info('Quality was missing in name, assuming it\'s a DVD-Rip based on the size: %s', size)
                found['dvdrip'] = True

        # Allow other qualities
        for allowed in preferred_quality.get('allow'):
            if found.get(allowed):
                del found[allowed]

        if found.get(preferred_quality['identifier']) and len(found) == 1:
            return False

        return found

    def correct3D(self, nzb, preferred_quality = None):
        if not preferred_quality: preferred_quality = {}
        if not preferred_quality.get('custom'): return

        threed = preferred_quality['custom'].get('3d')

        # Try guessing via quality tags
        guess = fireEvent('quality.guess', [nzb.get('name')], single = True)

        return threed == guess.get('is_3d')

    def correctYear(self, haystack, year, year_range):

        if not isinstance(haystack, (list, tuple, set)):
            haystack = [haystack]

        year_name = {}
        for string in haystack:

            year_name = fireEvent('scanner.name_year', string, single = True)

            if year_name and ((year - year_range) <= year_name.get('year') <= (year + year_range)):
                log.debug('Movie year matches range: %s looking for %s', (year_name.get('year'), year))
                return True

        log.debug('Movie year doesn\'t matche range: %s looking for %s', (year_name.get('year'), year))
        return False

    def correctName(self, check_name, movie_name):

        check_names = [check_name]

        # Match names between "
        try: check_names.append(re.search(r'([\'"])[^\1]*\1', check_name).group(0))
        except: pass

        # Match longest name between []
        try: check_names.append(max(re.findall(r'[^[]*\[([^]]*)\]', check_name), key = len).strip())
        except: pass

        for check_name in removeDuplicate(check_names):
            check_movie = fireEvent('scanner.name_year', check_name, single = True)

            try:
                check_words = removeEmpty(re.split('\W+', check_movie.get('name', '')))
                movie_words = removeEmpty(re.split('\W+', simplifyString(movie_name)))

                if len(check_words) > 0 and len(movie_words) > 0 and len(list(set(check_words) - set(movie_words))) == 0:
                    return True
            except:
                pass

        return False

    def correctWords(self, rel_name, media):
        media_title = fireEvent('searcher.get_search_title', media, single = True)
        media_words = re.split('\W+', simplifyString(media_title))

        rel_name = simplifyString(rel_name)
        rel_words = re.split('\W+', rel_name)

        # Make sure it has required words
        required_words = splitString(self.conf('required_words', section = 'searcher').lower())
        try: required_words = removeDuplicate(required_words + splitString(media['category']['required'].lower()))
        except: pass

        req_match = 0
        for req_set in required_words:
            req = splitString(req_set, '&')
            req_match += len(list(set(rel_words) & set(req))) == len(req)

        if len(required_words) > 0 and req_match == 0:
            log.info2('Wrong: Required word missing: %s', rel_name)
            return False

        # Ignore releases
        ignored_words = splitString(self.conf('ignored_words', section = 'searcher').lower())
        try: ignored_words = removeDuplicate(ignored_words + splitString(media['category']['ignored'].lower()))
        except: pass

        ignored_match = 0
        for ignored_set in ignored_words:
            ignored = splitString(ignored_set, '&')
            ignored_match += len(list(set(rel_words) & set(ignored))) == len(ignored)

        if len(ignored_words) > 0 and ignored_match:
            log.info2("Wrong: '%s' contains 'ignored words'", rel_name)
            return False

        # Ignore porn stuff
        pron_tags = ['xxx', 'sex', 'anal', 'tits', 'fuck', 'porn', 'orgy', 'milf', 'boobs', 'erotica', 'erotic', 'cock', 'dick']
        pron_words = list(set(rel_words) & set(pron_tags) - set(media_words))
        if pron_words:
            log.info('Wrong: %s, probably pr0n', rel_name)
            return False

        return True

class SearchSetupError(Exception):
    pass
