import datetime
import re
import time

from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.variable import splitString, removeEmpty, removeDuplicate, getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.base import SearcherBase
from couchpotato.environment import Env


log = CPLog(__name__)


class Searcher(SearcherBase):

    # noinspection PyMissingConstructor
    def __init__(self):
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

    def containsOtherQuality(self, nzb, movie_year = None, preferred_quality = None, types = None):
        if not preferred_quality: preferred_quality = {}

        found = {}

        # Try guessing via quality tags
        guess = fireEvent('quality.guess', files = [nzb.get('name')], size = nzb.get('size', None), types = types, single = True)

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
        for allowed in preferred_quality.get('allow', []):
            if found.get(allowed):
                del found[allowed]

        if found.get(preferred_quality['identifier']) and len(found) == 1:
            return False

        return found

    def correct3D(self, nzb, preferred_quality = None, types = None):
        if not preferred_quality: preferred_quality = {}
        if not preferred_quality.get('custom'): return

        threed = preferred_quality['custom'].get('3d')

        # Try guessing via quality tags
        guess = fireEvent('quality.guess', [nzb.get('name')], types = types, single = True)

        if guess:
            return threed == guess.get('is_3d')
        # If no quality guess, assume not 3d
        else:
            return threed == False

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

    def containsWords(self, rel_name, rel_words, conf, media):

        # Make sure it has required words
        words = splitString(self.conf('%s_words' % conf, section = 'searcher').lower())
        try: words = removeDuplicate(words + splitString(media['category'][conf].lower()))
        except: pass

        req_match = 0
        for req_set in words:
            if len(req_set) >= 2 and (req_set[:1] + req_set[-1:]) == '//':
                if re.search(req_set[1:-1], rel_name):
                    log.debug('Regex match: %s', req_set[1:-1])
                    req_match += 1
            else:
                req = splitString(req_set, '&')
                req_match += len(list(set(rel_words) & set(req))) == len(req)

        return words, req_match > 0

    def correctWords(self, rel_name, media):
        media_title = fireEvent('searcher.get_search_title', media, single = True)
        media_words = re.split('\W+', simplifyString(media_title))

        rel_name = simplifyString(rel_name)
        rel_words = re.split('\W+', rel_name)

        required_words, contains_required = self.containsWords(rel_name, rel_words, 'required', media)
        if len(required_words) > 0 and not contains_required:
            log.info2('Wrong: Required word missing: %s', rel_name)
            return False

        ignored_words, contains_ignored = self.containsWords(rel_name, rel_words, 'ignored', media)
        if len(ignored_words) > 0 and contains_ignored:
            log.info2("Wrong: '%s' contains 'ignored words'", rel_name)
            return False

        # Ignore porn stuff
        pron_tags = ['xxx', 'sex', 'anal', 'tits', 'fuck', 'porn', 'orgy', 'milf', 'boobs', 'erotica', 'erotic', 'cock', 'dick']
        pron_words = list(set(rel_words) & set(pron_tags) - set(media_words))
        if pron_words:
            log.info('Wrong: %s, probably pr0n', rel_name)
            return False

        return True

    def correctRelease(self, nzb = None, media = None, quality = None, **kwargs):
        raise NotImplementedError

    def couldBeReleased(self, is_pre_release, dates, media):
        raise NotImplementedError

    def getTitle(self, media):
        return getTitle(media)

    def getProfileId(self, media):
        # Required because the profile_id for an show episode is stored with
        # the show, not the episode.
        raise NotImplementedError

    def single(self, media, search_protocols = None, manual = False, force_download = False, notify = True):

        # Find out search type
        try:
            if not search_protocols:
                search_protocols = self.getSearchProtocols()
        except SearchSetupError:
            return

        db = get_db()
        profile = db.get('id', self.getProfileId(media))

        if not profile or (media['status'] == 'done' and not manual):
            log.debug('Media does not have a profile or already done, assuming in manage tab.')
            fireEvent('media.restatus', media['_id'], single = True)
            return

        default_title = self.getTitle(media)
        if not default_title:
            log.error('No proper info found for media, removing it from library to stop it from causing more issues.')
            fireEvent('media.delete', media['_id'], single = True)
            return

        # Update media status and check if it is still not done (due to the stop searching after feature
        if fireEvent('media.restatus', media['_id'], single = True) == 'done':
            log.debug('No better quality found, marking media %s as done.', default_title)

        pre_releases = fireEvent('quality.pre_releases', single = True)
        release_dates = fireEvent('media.update_release_dates', media['_id'], merge = True)

        found_releases = []
        previous_releases = media.get('releases', [])
        too_early_to_search = []
        outside_eta_results = 0
        always_search = self.conf('always_search')
        ignore_eta = manual
        total_result_count = 0

        if notify:
            fireEvent('notify.frontend', type = '%s.searcher.started' % self._type, data = {'_id': media['_id']}, message = 'Searching for "%s"' % default_title)

        # Ignore eta once every 7 days
        if not always_search:
            prop_name = 'last_ignored_eta.%s' % media['_id']
            last_ignored_eta = float(Env.prop(prop_name, default = 0))
            if last_ignored_eta < time.time() - 604800:
                ignore_eta = True
                Env.prop(prop_name, value = time.time())

        ret = False

        for index, q_identifier in enumerate(profile.get('qualities', [])):
            quality_custom = {
                'index': index,
                'quality': q_identifier,
                'finish': profile['finish'][index],
                'wait_for': tryInt(profile['wait_for'][index]),
                '3d': profile['3d'][index] if profile.get('3d') else False,
                'minimum_score': profile.get('minimum_score', 1),
            }

            could_not_be_released = not self.couldBeReleased(q_identifier in pre_releases, release_dates, media)
            if not always_search and could_not_be_released:
                too_early_to_search.append(q_identifier)

                # Skip release, if ETA isn't ignored
                if not ignore_eta:
                    continue

            has_better_quality = 0

            # See if better quality is available
            for release in media.get('releases', []):
                if release['status'] not in ['available', 'ignored', 'failed']:
                    is_higher = fireEvent('quality.ishigher', \
                            {'identifier': q_identifier, 'is_3d': quality_custom.get('3d', 0)}, \
                            {'identifier': release['quality'], 'is_3d': release.get('is_3d', 0)}, \
                            profile, single = True)
                    if is_higher != 'higher':
                        has_better_quality += 1

            # Don't search for quality lower then already available.
            if has_better_quality > 0:
                log.info('Better quality (%s) already available or snatched for %s', (q_identifier, default_title))
                fireEvent('media.restatus', media['_id'], single = True)
                break

            quality = fireEvent('quality.single', identifier = q_identifier, single = True)
            log.info('Search for %s in %s%s', (default_title, quality['label'], ' ignoring ETA' if always_search or ignore_eta else ''))

            # Extend quality with profile customs
            quality['custom'] = quality_custom

            results = fireEvent('searcher.search', search_protocols, media, quality, single = True) or []

            # Check if media isn't deleted while searching
            if not fireEvent('media.get', media.get('_id'), single = True):
                break

            # Add them to this media releases list
            found_releases += fireEvent('release.create_from_search', results, media, quality, single = True)
            results_count = len(found_releases)
            total_result_count += results_count
            if results_count == 0:
                log.debug('Nothing found for %s in %s', (default_title, quality['label']))

            # Keep track of releases found outside ETA window
            outside_eta_results += results_count if could_not_be_released else 0

            # Don't trigger download, but notify user of available releases
            if could_not_be_released and results_count > 0:
                log.debug('Found %s releases for "%s", but ETA isn\'t correct yet.', (results_count, default_title))

            # Try find a valid result and download it
            if (force_download or not could_not_be_released or always_search) and fireEvent('release.try_download_result', results, media, quality_custom, single = True):
                ret = True

            # Remove releases that aren't found anymore
            temp_previous_releases = []
            for release in previous_releases:
                if release.get('status') == 'available' and release.get('identifier') not in found_releases:
                    fireEvent('release.delete', release.get('_id'), single = True)
                else:
                    temp_previous_releases.append(release)
            previous_releases = temp_previous_releases
            del temp_previous_releases

            # Break if CP wants to shut down
            if self.shuttingDown() or ret:
                break

        if total_result_count > 0:
            fireEvent('media.tag', media['_id'], 'recent', update_edited = True, single = True)

        if len(too_early_to_search) > 0:
            log.info2('Too early to search for %s, %s', (too_early_to_search, default_title))

            if outside_eta_results > 0:
                message = 'Found %s releases for "%s" before ETA. Select and download via the dashboard.' % (outside_eta_results, default_title)
                log.info(message)

                if not manual:
                    fireEvent('media.available', message = message, data = {})

        if notify:
            fireEvent('notify.frontend', type = '%s.searcher.ended' % self._type, data = {'_id': media['_id']})

        return ret

class SearchSetupError(Exception):
    pass
