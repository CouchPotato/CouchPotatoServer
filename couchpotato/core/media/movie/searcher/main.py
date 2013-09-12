from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.helpers.variable import md5, getTitle, splitString, \
    possibleTitles, getImdb
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.base import SearcherBase
from couchpotato.core.media.movie import MovieTypeBase
from couchpotato.core.settings.model import Media, Release, ReleaseInfo
from couchpotato.environment import Env
from datetime import date
from sqlalchemy.exc import InterfaceError
import random
import re
import time
import traceback

log = CPLog(__name__)


class MovieSearcher(SearcherBase, MovieTypeBase):

    in_progress = False

    def __init__(self):
        super(MovieSearcher, self).__init__()

        addEvent('movie.searcher.all', self.searchAll)
        addEvent('movie.searcher.all_view', self.searchAllView)
        addEvent('movie.searcher.single', self.single)
        addEvent('movie.searcher.correct_movie', self.correctMovie)
        addEvent('movie.searcher.try_next_release', self.tryNextRelease)
        addEvent('movie.searcher.could_be_released', self.couldBeReleased)

        addApiView('movie.searcher.try_next', self.tryNextReleaseView, docs = {
            'desc': 'Marks the snatched results as ignored and try the next best release',
            'params': {
                'id': {'desc': 'The id of the movie'},
            },
        })

        addApiView('movie.searcher.full_search', self.searchAllView, docs = {
            'desc': 'Starts a full search for all wanted movies',
        })

        addApiView('movie.searcher.progress', self.getProgress, docs = {
            'desc': 'Get the progress of current full search',
            'return': {'type': 'object', 'example': """{
    'progress': False || object, total & to_go,
}"""},
        })

        if self.conf('run_on_launch'):
            addEvent('app.load', self.searchAll)

    def searchAllView(self, **kwargs):

        fireEventAsync('movie.searcher.all')

        return {
            'success': not self.in_progress
        }

    def searchAll(self):

        if self.in_progress:
            log.info('Search already in progress')
            fireEvent('notify.frontend', type = 'movie.searcher.already_started', data = True, message = 'Full search already in progress')
            return

        self.in_progress = True
        fireEvent('notify.frontend', type = 'movie.searcher.started', data = True, message = 'Full search started')

        db = get_session()

        movies = db.query(Media).filter(
            Media.status.has(identifier = 'active')
        ).all()
        random.shuffle(movies)

        self.in_progress = {
            'total': len(movies),
            'to_go': len(movies),
        }

        try:
            search_protocols = fireEvent('searcher.protocols', single = True)

            for movie in movies:
                movie_dict = movie.to_dict({
                    'category': {},
                    'profile': {'types': {'quality': {}}},
                    'releases': {'status': {}, 'quality': {}},
                    'library': {'titles': {}, 'files':{}},
                    'files': {},
                })

                try:
                    self.single(movie_dict, search_protocols)
                except IndexError:
                    log.error('Forcing library update for %s, if you see this often, please report: %s', (movie_dict['library']['identifier'], traceback.format_exc()))
                    fireEvent('library.update.movie', movie_dict['library']['identifier'], force = True)
                except:
                    log.error('Search failed for %s: %s', (movie_dict['library']['identifier'], traceback.format_exc()))

                self.in_progress['to_go'] -= 1

                # Break if CP wants to shut down
                if self.shuttingDown():
                    break

        except SearchSetupError:
            pass

        self.in_progress = False

    def single(self, movie, search_protocols = None, manual = False):

        # Find out search type
        try:
            if not search_protocols:
                search_protocols = fireEvent('searcher.protocols', single = True)
        except SearchSetupError:
            return

        done_status = fireEvent('status.get', 'done', single = True)

        if not movie['profile'] or (movie['status_id'] == done_status.get('id') and not manual):
            log.debug('Movie doesn\'t have a profile or already done, assuming in manage tab.')
            return

        db = get_session()

        pre_releases = fireEvent('quality.pre_releases', single = True)
        release_dates = fireEvent('library.update.movie.release_date', identifier = movie['library']['identifier'], merge = True)
        available_status, ignored_status, failed_status = fireEvent('status.get', ['available', 'ignored', 'failed'], single = True)

        found_releases = []
        too_early_to_search = []

        default_title = getTitle(movie['library'])
        if not default_title:
            log.error('No proper info found for movie, removing it from library to cause it from having more issues.')
            fireEvent('movie.delete', movie['id'], single = True)
            return

        fireEvent('notify.frontend', type = 'movie.searcher.started.%s' % movie['id'], data = True, message = 'Searching for "%s"' % default_title)


        ret = False
        for quality_type in movie['profile']['types']:
            if not self.conf('always_search') and not self.couldBeReleased(quality_type['quality']['identifier'] in pre_releases, release_dates, movie['library']['year']):
                too_early_to_search.append(quality_type['quality']['identifier'])
                continue

            has_better_quality = 0

            # See if better quality is available
            for release in movie['releases']:
                if release['quality']['order'] <= quality_type['quality']['order'] and release['status_id'] not in [available_status.get('id'), ignored_status.get('id'), failed_status.get('id')]:
                    has_better_quality += 1

            # Don't search for quality lower then already available.
            if has_better_quality is 0:

                log.info('Search for %s in %s', (default_title, quality_type['quality']['label']))
                quality = fireEvent('quality.single', identifier = quality_type['quality']['identifier'], single = True)

                results = []
                for search_protocol in search_protocols:
                    protocol_results = fireEvent('provider.search.%s.movie' % search_protocol, movie, quality, merge = True)
                    if protocol_results:
                        results += protocol_results

                sorted_results = sorted(results, key = lambda k: k['score'], reverse = True)
                if len(sorted_results) == 0:
                    log.debug('Nothing found for %s in %s', (default_title, quality_type['quality']['label']))

                download_preference = self.conf('preferred_method', section = 'searcher')
                if download_preference != 'both':
                    sorted_results = sorted(sorted_results, key = lambda k: k['protocol'][:3], reverse = (download_preference == 'torrent'))

                # Check if movie isn't deleted while searching
                if not db.query(Media).filter_by(id = movie.get('id')).first():
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

                    if nzb['status_id'] in [ignored_status.get('id'), failed_status.get('id')]:
                        log.info('Ignored: %s', nzb['name'])
                        continue

                    if nzb['score'] <= 0:
                        log.info('Ignored, score to low: %s', nzb['name'])
                        continue

                    downloaded = fireEvent('searcher.download', data = nzb, movie = movie, manual = manual, single = True)
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

        if len(too_early_to_search) > 0:
            log.info2('Too early to search for %s, %s', (too_early_to_search, default_title))

        fireEvent('notify.frontend', type = 'movie.searcher.ended.%s' % movie['id'], data = True)

        return ret

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
        required_words = splitString(self.conf('required_words', section = 'searcher').lower())
        try: required_words = list(set(required_words + splitString(movie['category']['required'].lower())))
        except: pass

        req_match = 0
        for req_set in required_words:
            req = splitString(req_set, '&')
            req_match += len(list(set(nzb_words) & set(req))) == len(req)

        if len(required_words) > 0  and req_match == 0:
            log.info2('Wrong: Required word missing: %s', nzb['name'])
            return False

        # Ignore releases
        ignored_words = splitString(self.conf('ignored_words', section = 'searcher').lower())
        try: ignored_words = list(set(ignored_words + splitString(movie['category']['ignored'].lower())))
        except: pass

        ignored_match = 0
        for ignored_set in ignored_words:
            ignored = splitString(ignored_set, '&')
            ignored_match += len(list(set(nzb_words) & set(ignored))) == len(ignored)

        if len(ignored_words) > 0 and ignored_match:
            log.info2("Wrong: '%s' contains 'ignored words'", (nzb['name']))
            return False

        # Ignore porn stuff
        pron_tags = ['xxx', 'sex', 'anal', 'tits', 'fuck', 'porn', 'orgy', 'milf', 'boobs', 'erotica', 'erotic']
        pron_words = list(set(nzb_words) & set(pron_tags) - set(movie_words))
        if pron_words:
            log.info('Wrong: %s, probably pr0n', (nzb['name']))
            return False

        preferred_quality = fireEvent('quality.single', identifier = quality['identifier'], single = True)

        # Contains lower quality string
        if fireEvent('searcher.contains_other_quality', nzb, movie_year = movie['library']['year'], preferred_quality = preferred_quality, single = True):
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
        if getImdb(nzb.get('description', '')) == movie['library']['identifier']:
            return True

        for raw_title in movie['library']['titles']:
            for movie_title in possibleTitles(raw_title['title']):
                movie_words = re.split('\W+', simplifyString(movie_title))

                if fireEvent('searcher.correct_name', nzb['name'], movie_title, single = True):
                    # if no IMDB link, at least check year range 1
                    if len(movie_words) > 2 and fireEvent('searcher.correct_year', nzb['name'], movie['library']['year'], 1, single = True):
                        return True

                    # if no IMDB link, at least check year
                    if len(movie_words) <= 2 and fireEvent('searcher.correct_year', nzb['name'], movie['library']['year'], 0, single = True):
                        return True

        log.info("Wrong: %s, undetermined naming. Looking for '%s (%s)'", (nzb['name'], movie_name, movie['library']['year']))
        return False

    def couldBeReleased(self, is_pre_release, dates, year = None):

        now = int(time.time())
        now_year = date.today().year

        if (year is None or year < now_year - 1) and (not dates or (dates.get('theater', 0) == 0 and dates.get('dvd', 0) == 0)):
            return True
        else:

            # For movies before 1972
            if not dates or dates.get('theater', 0) < 0 or dates.get('dvd', 0) < 0:
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

    def tryNextReleaseView(self, id = None, **kwargs):

        trynext = self.tryNextRelease(id, manual = True)

        return {
            'success': trynext
        }

    def tryNextRelease(self, movie_id, manual = False):

        snatched_status, done_status, ignored_status = fireEvent('status.get', ['snatched', 'done', 'ignored'], single = True)

        try:
            db = get_session()
            rels = db.query(Release) \
                .filter_by(movie_id = movie_id) \
                .filter(Release.status_id.in_([snatched_status.get('id'), done_status.get('id')])) \
                .all()

            for rel in rels:
                rel.status_id = ignored_status.get('id')
            db.commit()

            movie_dict = fireEvent('movie.get', movie_id, single = True)
            log.info('Trying next release for: %s', getTitle(movie_dict['library']))
            fireEvent('movie.searcher.single', movie_dict, manual = manual)

            return True

        except:
            log.error('Failed searching for next release: %s', traceback.format_exc())
            return False

class SearchSetupError(Exception):
    pass
