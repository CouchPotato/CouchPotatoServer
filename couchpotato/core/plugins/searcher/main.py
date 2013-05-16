from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.helpers.request import jsonified, getParam
from couchpotato.core.helpers.variable import md5, getTitle, splitString, \
    possibleTitles
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Movie, Release, ReleaseInfo
from couchpotato.environment import Env
from inspect import ismethod, isfunction
from sqlalchemy.exc import InterfaceError
import datetime
import random
import re
import time
import traceback

log = CPLog(__name__)


class Searcher(Plugin):

    in_progress = False

    def __init__(self):
        addEvent('searcher.all', self.allMovies)
        addEvent('searcher.single', self.single)
        addEvent('searcher.correct_movie', self.correctMovie)
        addEvent('searcher.download', self.download)
        addEvent('searcher.try_next_release', self.tryNextRelease)
        addEvent('searcher.could_be_released', self.couldBeReleased)

        addApiView('searcher.try_next', self.tryNextReleaseView, docs = {
            'desc': 'Marks the snatched results as ignored and try the next best release',
            'params': {
                'id': {'desc': 'The id of the movie'},
            },
        })

        addApiView('searcher.full_search', self.allMoviesView, docs = {
            'desc': 'Starts a full search for all wanted movies',
        })

        addApiView('searcher.progress', self.getProgress, docs = {
            'desc': 'Get the progress of current full search',
            'return': {'type': 'object', 'example': """{
    'progress': False || object, total & to_go,
}"""},
        })

        addEvent('app.load', self.setCrons)
        addEvent('setting.save.searcher.cron_day.after', self.setCrons)
        addEvent('setting.save.searcher.cron_hour.after', self.setCrons)
        addEvent('setting.save.searcher.cron_minute.after', self.setCrons)

    def setCrons(self):
        fireEvent('schedule.cron', 'searcher.all', self.allMovies, day = self.conf('cron_day'), hour = self.conf('cron_hour'), minute = self.conf('cron_minute'))

    def allMoviesView(self):

        in_progress = self.in_progress
        if not in_progress:
            fireEventAsync('searcher.all')
            fireEvent('notify.frontend', type = 'searcher.started', data = True, message = 'Full search started')
        else:
            fireEvent('notify.frontend', type = 'searcher.already_started', data = True, message = 'Full search already in progress')

        return jsonified({
            'success': not in_progress
        })

    def getProgress(self):

        return jsonified({
            'progress': self.in_progress
        })

    def allMovies(self):

        if self.in_progress:
            log.info('Search already in progress')
            return

        self.in_progress = True

        db = get_session()

        movies = db.query(Movie).filter(
            Movie.status.has(identifier = 'active')
        ).all()
        random.shuffle(movies)

        self.in_progress = {
            'total': len(movies),
            'to_go': len(movies),
        }

        try:
            search_types = self.getSearchTypes()

            for movie in movies:
                movie_dict = movie.to_dict({
                    'profile': {'types': {'quality': {}}},
                    'releases': {'status': {}, 'quality': {}},
                    'library': {'titles': {}, 'files':{}},
                    'files': {}
                })

                try:
                    self.single(movie_dict, search_types)
                except IndexError:
                    log.error('Forcing library update for %s, if you see this often, please report: %s', (movie_dict['library']['identifier'], traceback.format_exc()))
                    fireEvent('library.update', movie_dict['library']['identifier'], force = True)
                except:
                    log.error('Search failed for %s: %s', (movie_dict['library']['identifier'], traceback.format_exc()))

                self.in_progress['to_go'] -= 1

                # Break if CP wants to shut down
                if self.shuttingDown():
                    break

        except SearchSetupError:
            pass

        self.in_progress = False

    def single(self, movie, search_types = None):

        # Find out search type
        try:
            if not search_types:
                search_types = self.getSearchTypes()
        except SearchSetupError:
            return

        done_status = fireEvent('status.get', 'done', single = True)

        if not movie['profile'] or movie['status_id'] == done_status.get('id'):
            log.debug('Movie doesn\'t have a profile or already done, assuming in manage tab.')
            return

        db = get_session()

        pre_releases = fireEvent('quality.pre_releases', single = True)
        release_dates = fireEvent('library.update_release_date', identifier = movie['library']['identifier'], merge = True)
        available_status, ignored_status = fireEvent('status.get', ['available', 'ignored'], single = True)

        found_releases = []

        default_title = getTitle(movie['library'])
        if not default_title:
            log.error('No proper info found for movie, removing it from library to cause it from having more issues.')
            fireEvent('movie.delete', movie['id'], single = True)
            return

        fireEvent('notify.frontend', type = 'searcher.started.%s' % movie['id'], data = True, message = 'Searching for "%s"' % default_title)


        ret = False
        for quality_type in movie['profile']['types']:
            if not self.conf('always_search') and not self.couldBeReleased(quality_type['quality']['identifier'] in pre_releases, release_dates):
                log.info('Too early to search for %s, %s', (quality_type['quality']['identifier'], default_title))
                continue

            has_better_quality = 0

            # See if better quality is available
            for release in movie['releases']:
                if release['quality']['order'] <= quality_type['quality']['order'] and release['status_id'] not in [available_status.get('id'), ignored_status.get('id')]:
                    has_better_quality += 1

            # Don't search for quality lower then already available.
            if has_better_quality is 0:

                log.info('Search for %s in %s', (default_title, quality_type['quality']['label']))
                quality = fireEvent('quality.single', identifier = quality_type['quality']['identifier'], single = True)

                results = []
                for search_type in search_types:
                    type_results = fireEvent('%s.search' % search_type, movie, quality, merge = True)
                    if type_results:
                        results += type_results

                sorted_results = sorted(results, key = lambda k: k['score'], reverse = True)
                if len(sorted_results) == 0:
                    log.debug('Nothing found for %s in %s', (default_title, quality_type['quality']['label']))

                download_preference = self.conf('preferred_method')
                if download_preference != 'both':
                    sorted_results = sorted(sorted_results, key = lambda k: k['type'], reverse = (download_preference == 'torrent'))

                # Check if movie isn't deleted while searching
                if not db.query(Movie).filter_by(id = movie.get('id')).first():
                    break

                # Add them to this movie releases list
                for nzb in sorted_results:

                    nzb_identifier = md5(nzb['url'])
                    found_releases.append(nzb_identifier)

                    rls = db.query(Release).filter_by(identifier = nzb_identifier).first()
                    if not rls:
                        rls = Release(
                            identifier = nzb_identifier,
                            movie_id = movie.get('id'),
                            quality_id = quality_type.get('quality_id'),
                            status_id = available_status.get('id')
                        )
                        db.add(rls)
                    else:
                        [db.delete(old_info) for old_info in rls.info]
                        rls.last_edit = int(time.time())

                    db.commit()

                    for info in nzb:
                        try:
                            if not isinstance(nzb[info], (str, unicode, int, long, float)):
                                continue

                            rls_info = ReleaseInfo(
                                identifier = info,
                                value = toUnicode(nzb[info])
                            )
                            rls.info.append(rls_info)
                        except InterfaceError:
                            log.debug('Couldn\'t add %s to ReleaseInfo: %s', (info, traceback.format_exc()))

                    db.commit()

                    nzb['status_id'] = rls.status_id


                for nzb in sorted_results:
                    if not quality_type.get('finish', False) and quality_type.get('wait_for', 0) > 0 and nzb.get('age') <= quality_type.get('wait_for', 0):
                        log.info('Ignored, waiting %s days: %s', (quality_type.get('wait_for'), nzb['name']))
                        continue

                    if nzb['status_id'] == ignored_status.get('id'):
                        log.info('Ignored: %s', nzb['name'])
                        continue

                    if nzb['score'] <= 0:
                        log.info('Ignored, score to low: %s', nzb['name'])
                        continue

                    downloaded = self.download(data = nzb, movie = movie)
                    if downloaded is True:
                        ret = True
                        break
                    elif downloaded != 'try_next':
                        break

                # Remove releases that aren't found anymore
                for release in movie.get('releases', []):
                    if release.get('status_id') == available_status.get('id') and release.get('identifier') not in found_releases:
                        fireEvent('release.delete', release.get('id'), single = True)

            else:
                log.info('Better quality (%s) already available or snatched for %s', (quality_type['quality']['label'], default_title))
                fireEvent('movie.restatus', movie['id'])
                break

            # Break if CP wants to shut down
            if self.shuttingDown() or ret:
                break

        fireEvent('notify.frontend', type = 'searcher.ended.%s' % movie['id'], data = True)

        return ret

    def download(self, data, movie, manual = False):

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
                                            mvie = db.query(Movie).filter_by(id = movie['id']).first()
                                            mvie.status_id = done_status.get('id')
                                            mvie.last_edit = int(time.time())
                                            db.commit()
                            except:
                                log.error('Failed marking movie finished, renamer disabled: %s', traceback.format_exc())

                except:
                    log.error('Failed marking movie finished: %s', traceback.format_exc())

                return True

        log.info('Tried to download, but none of the "%s" downloaders are enabled or gave an error', (data.get('type', '')))

        return False

    def getSearchTypes(self):

        download_types = fireEvent('download.enabled_types', merge = True)
        provider_types = fireEvent('provider.enabled_types', merge = True)

        if download_types and len(list(set(provider_types) & set(download_types))) == 0:
            log.error('There aren\'t any providers enabled for your downloader (%s). Check your settings.', ','.join(download_types))
            raise NoProviders

        for useless_provider in list(set(provider_types) - set(download_types)):
            log.debug('Provider for "%s" enabled, but no downloader.', useless_provider)

        search_types = download_types

        if len(search_types) == 0:
            log.error('There aren\'t any downloaders enabled. Please pick one in settings.')
            raise NoDownloaders

        return search_types

    def correctMovie(self, nzb = None, movie = None, quality = None, **kwargs):

        imdb_results = kwargs.get('imdb_results', False)
        retention = Env.setting('retention', section = 'nzb')

        if nzb.get('seeders') is None and 0 < retention < nzb.get('age', 0):
            log.info2('Wrong: Outside retention, age is %s, needs %s or lower: %s', (nzb['age'], retention, nzb['name']))
            return False

        movie_name = getTitle(movie['library'])
        movie_words = re.split('\W+', simplifyString(movie_name))
        nzb_name = simplifyString(nzb['name'])
        nzb_words = re.split('\W+', nzb_name)

        # Make sure it has required words
        required_words = splitString(self.conf('required_words').lower())
        req_match = 0
        for req_set in required_words:
            req = splitString(req_set, '&')
            req_match += len(list(set(nzb_words) & set(req))) == len(req)

        if self.conf('required_words') and req_match == 0:
            log.info2("Wrong: Required word missing: %s" % nzb['name'])
            return False

        # Ignore releases
        ignored_words = splitString(self.conf('ignored_words').lower())
        ignored_match = 0
        for ignored_set in ignored_words:
            ignored = splitString(ignored_set, '&')
            ignored_match += len(list(set(nzb_words) & set(ignored))) == len(ignored)

        if self.conf('ignored_words') and ignored_match:
            log.info2("Wrong: '%s' contains 'ignored words'" % (nzb['name']))
            return False

        # Ignore porn stuff
        pron_tags = ['xxx', 'sex', 'anal', 'tits', 'fuck', 'porn', 'orgy', 'milf', 'boobs', 'erotica', 'erotic']
        pron_words = list(set(nzb_words) & set(pron_tags) - set(movie_words))
        if pron_words:
            log.info('Wrong: %s, probably pr0n', (nzb['name']))
            return False

        preferred_quality = fireEvent('quality.single', identifier = quality['identifier'], single = True)

        # Contains lower quality string
        if self.containsOtherQuality(nzb, movie_year = movie['library']['year'], preferred_quality = preferred_quality):
            log.info2('Wrong: %s, looking for %s', (nzb['name'], quality['label']))
            return False


        # File to small
        if nzb['size'] and preferred_quality['size_min'] > nzb['size']:
            log.info2('Wrong: "%s" is too small to be %s. %sMB instead of the minimal of %sMB.', (nzb['name'], preferred_quality['label'], nzb['size'], preferred_quality['size_min']))
            return False

        # File to large
        if nzb['size'] and preferred_quality.get('size_max') < nzb['size']:
            log.info2('Wrong: "%s" is too large to be %s. %sMB instead of the maximum of %sMB.', (nzb['name'], preferred_quality['label'], nzb['size'], preferred_quality['size_max']))
            return False


        # Provider specific functions
        get_more = nzb.get('get_more_info')
        if get_more:
            get_more(nzb)

        extra_check = nzb.get('extra_check')
        if extra_check and not extra_check(nzb):
            return False


        if imdb_results:
            return True

        # Check if nzb contains imdb link
        if self.checkIMDB([nzb.get('description', '')], movie['library']['identifier']):
            return True

        for raw_title in movie['library']['titles']:
            for movie_title in possibleTitles(raw_title['title']):
                movie_words = re.split('\W+', simplifyString(movie_title))

                if self.correctName(nzb['name'], movie_title):
                    # if no IMDB link, at least check year range 1
                    if len(movie_words) > 2 and self.correctYear([nzb['name']], movie['library']['year'], 1):
                        return True

                    # if no IMDB link, at least check year
                    if len(movie_words) <= 2 and self.correctYear([nzb['name']], movie['library']['year'], 0):
                        return True

        log.info("Wrong: %s, undetermined naming. Looking for '%s (%s)'" % (nzb['name'], movie_name, movie['library']['year']))
        return False

    def containsOtherQuality(self, nzb, movie_year = None, preferred_quality = {}):

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
                log.info('Quality was missing in name, assuming it\'s a DVD-R based on the size: %s', (size))
                found['dvdr'] = True
            else: # Assume dvdrip
                log.info('Quality was missing in name, assuming it\'s a DVD-Rip based on the size: %s', (size))
                found['dvdrip'] = True

        # Allow other qualities
        for allowed in preferred_quality.get('allow'):
            if found.get(allowed):
                del found[allowed]

        return not (found.get(preferred_quality['identifier']) and len(found) == 1)

    def checkIMDB(self, haystack, imdbId):

        for string in haystack:
            if 'imdb.com/title/' + imdbId in string:
                return True

        return False

    def correctYear(self, haystack, year, year_range):

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

    def couldBeReleased(self, is_pre_release, dates):

        now = int(time.time())

        if not dates or (dates.get('theater', 0) == 0 and dates.get('dvd', 0) == 0):
            return True
        else:

            # For movies before 1972
            if dates.get('theater', 0) < 0 or dates.get('dvd', 0) < 0:
                return True

            if is_pre_release:
                # Prerelease 1 week before theaters
                if dates.get('theater') - 604800 < now:
                    return True
            else:
                # 12 weeks after theater release
                if dates.get('theater') > 0 and dates.get('theater') + 7257600 < now:
                    return True

                if dates.get('dvd') > 0:

                    # 4 weeks before dvd release
                    if dates.get('dvd') - 2419200 < now:
                        return True

                    # Dvd should be released
                    if dates.get('dvd') < now:
                        return True


        return False

    def tryNextReleaseView(self):

        trynext = self.tryNextRelease(getParam('id'))

        return jsonified({
            'success': trynext
        })

    def tryNextRelease(self, movie_id, manual = False):

        snatched_status = fireEvent('status.get', 'snatched', single = True)
        ignored_status = fireEvent('status.get', 'ignored', single = True)

        try:
            db = get_session()
            rels = db.query(Release).filter_by(
               status_id = snatched_status.get('id'),
               movie_id = movie_id
            ).all()

            for rel in rels:
                rel.status_id = ignored_status.get('id')
            db.commit()

            movie_dict = fireEvent('movie.get', movie_id, single = True)
            log.info('Trying next release for: %s', getTitle(movie_dict['library']))
            fireEvent('searcher.single', movie_dict)

            return True

        except:
            log.error('Failed searching for next release: %s', traceback.format_exc())
            return False

class SearchSetupError(Exception):
    pass

class NoDownloaders(SearchSetupError):
    pass

class NoProviders(SearchSetupError):
    pass
