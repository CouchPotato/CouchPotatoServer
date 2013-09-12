from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.helpers.variable import md5, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.base import SearcherBase
from couchpotato.core.settings.model import Media, Release, ReleaseInfo
from couchpotato.environment import Env
from inspect import ismethod, isfunction
import datetime
import re
import time
import traceback

log = CPLog(__name__)


class Searcher(SearcherBase):

    def __init__(self):
        addEvent('searcher.protocols', self.getSearchProtocols)
        addEvent('searcher.contains_other_quality', self.containsOtherQuality)
        addEvent('searcher.correct_year', self.correctYear)
        addEvent('searcher.correct_name', self.correctName)
        addEvent('searcher.download', self.download)

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

    def download(self, data, movie, manual = False):

        if not data.get('protocol'):
            data['protocol'] = data['type']
            data['type'] = 'movie'

        # Test to see if any downloaders are enabled for this type
        downloader_enabled = fireEvent('download.enabled', manual, data, single = True)

        if downloader_enabled:

            snatched_status = fireEvent('status.get', 'snatched', single = True)

            # Download movie to temp
            filedata = None
            if data.get('download') and (ismethod(data.get('download')) or isfunction(data.get('download'))):
                filedata = data.get('download')(url = data.get('url'), nzb_id = data.get('id'))
                if filedata == 'try_next':
                    return filedata

            download_result = fireEvent('download', data = data, movie = movie, manual = manual, filedata = filedata, single = True)
            log.debug('Downloader result: %s', download_result)

            if download_result:
                try:
                    # Mark release as snatched
                    db = get_session()
                    rls = db.query(Release).filter_by(identifier = md5(data['url'])).first()
                    if rls:
                        renamer_enabled = Env.setting('enabled', 'renamer')

                        done_status = fireEvent('status.get', 'done', single = True)
                        rls.status_id = done_status.get('id') if not renamer_enabled else snatched_status.get('id')

                        # Save download-id info if returned
                        if isinstance(download_result, dict):
                            for key in download_result:
                                rls_info = ReleaseInfo(
                                    identifier = 'download_%s' % key,
                                    value = toUnicode(download_result.get(key))
                                )
                                rls.info.append(rls_info)
                        db.commit()

                        log_movie = '%s (%s) in %s' % (getTitle(movie['library']), movie['library']['year'], rls.quality.label)
                        snatch_message = 'Snatched "%s": %s' % (data.get('name'), log_movie)
                        log.info(snatch_message)
                        fireEvent('movie.snatched', message = snatch_message, data = rls.to_dict())

                        # If renamer isn't used, mark movie done
                        if not renamer_enabled:
                            active_status = fireEvent('status.get', 'active', single = True)
                            done_status = fireEvent('status.get', 'done', single = True)
                            try:
                                if movie['status_id'] == active_status.get('id'):
                                    for profile_type in movie['profile']['types']:
                                        if profile_type['quality_id'] == rls.quality.id and profile_type['finish']:
                                            log.info('Renamer disabled, marking movie as finished: %s', log_movie)

                                            # Mark release done
                                            rls.status_id = done_status.get('id')
                                            rls.last_edit = int(time.time())
                                            db.commit()

                                            # Mark movie done
                                            mvie = db.query(Media).filter_by(id = movie['id']).first()
                                            mvie.status_id = done_status.get('id')
                                            mvie.last_edit = int(time.time())
                                            db.commit()
                            except:
                                log.error('Failed marking movie finished, renamer disabled: %s', traceback.format_exc())

                except:
                    log.error('Failed marking movie finished: %s', traceback.format_exc())

                return True

        log.info('Tried to download, but none of the "%s" downloaders are enabled or gave an error', (data.get('protocol')))

        return False

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

        name = nzb['name']
        size = nzb.get('size', 0)
        nzb_words = re.split('\W+', simplifyString(name))

        qualities = fireEvent('quality.all', single = True)

        found = {}
        for quality in qualities:
            # Main in words
            if quality['identifier'] in nzb_words:
                found[quality['identifier']] = True

            # Alt in words
            if list(set(nzb_words) & set(quality['alternative'])):
                found[quality['identifier']] = True

        # Try guessing via quality tags
        guess = fireEvent('quality.guess', [nzb.get('name')], single = True)
        if guess:
            found[guess['identifier']] = True

        # Hack for older movies that don't contain quality tag
        year_name = fireEvent('scanner.name_year', name, single = True)
        if len(found) == 0 and movie_year < datetime.datetime.now().year - 3 and not year_name.get('year', None):
            if size > 3000: # Assume dvdr
                log.info('Quality was missing in name, assuming it\'s a DVD-R based on the size: %s', size)
                found['dvdr'] = True
            else: # Assume dvdrip
                log.info('Quality was missing in name, assuming it\'s a DVD-Rip based on the size: %s', size)
                found['dvdrip'] = True

        # Allow other qualities
        for allowed in preferred_quality.get('allow'):
            if found.get(allowed):
                del found[allowed]

        return not (found.get(preferred_quality['identifier']) and len(found) == 1)

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
        try: check_names.append(max(check_name.split('['), key = len))
        except: pass

        for check_name in list(set(check_names)):
            check_movie = fireEvent('scanner.name_year', check_name, single = True)

            try:
                check_words = filter(None, re.split('\W+', check_movie.get('name', '')))
                movie_words = filter(None, re.split('\W+', simplifyString(movie_name)))

                if len(check_words) > 0 and len(movie_words) > 0 and len(list(set(check_words) - set(movie_words))) == 0:
                    return True
            except:
                pass

        return False

class SearchSetupError(Exception):
    pass
