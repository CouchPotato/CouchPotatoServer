from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.variable import getTitle, possibleTitles, getImdb
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.base import SearcherBase
from couchpotato.core.media.movie import MovieTypeBase
from couchpotato.core.settings.model import Media, Release
from couchpotato.environment import Env
from datetime import date
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
        addEvent('movie.searcher.try_next_release', self.tryNextRelease)
        addEvent('movie.searcher.could_be_released', self.couldBeReleased)
        addEvent('searcher.correct_release', self.correctRelease)
        addEvent('searcher.get_search_title', self.getSearchTitle)

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

        movies_raw = db.query(Media).filter(
            Media.status.has(identifier = 'active')
        ).all()

        random.shuffle(movies_raw)

        movies = []
        for m in movies_raw:
            movies.append(m.to_dict({
                'category': {},
                'profile': {'types': {'quality': {}}},
                'releases': {'status': {}, 'quality': {}},
                'library': {'titles': {}, 'files': {}},
                'files': {},
            }))

        self.in_progress = {
            'total': len(movies),
            'to_go': len(movies),
        }

        try:
            search_protocols = fireEvent('searcher.protocols', single = True)

            for movie in movies:

                try:
                    self.single(movie, search_protocols)
                except IndexError:
                    log.error('Forcing library update for %s, if you see this often, please report: %s', (movie['library']['identifier'], traceback.format_exc()))
                    fireEvent('library.update.movie', movie['library']['identifier'])
                except:
                    log.error('Search failed for %s: %s', (movie['library']['identifier'], traceback.format_exc()))

                self.in_progress['to_go'] -= 1

                # Break if CP wants to shut down
                if self.shuttingDown():
                    break

        except SearchSetupError:
            pass

        self.in_progress = False

    def single(self, movie, search_protocols = None, manual = False):

        # movies don't contain 'type' yet, so just set to default here
        if 'type' not in movie:
            movie['type'] = 'movie'

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

        pre_releases = fireEvent('quality.pre_releases', single = True)
        release_dates = fireEvent('library.update.movie.release_date', identifier = movie['library']['identifier'], merge = True)
        available_status, ignored_status, failed_status = fireEvent('status.get', ['available', 'ignored', 'failed'], single = True)

        found_releases = []
        too_early_to_search = []

        default_title = getTitle(movie['library'])
        if not default_title:
            log.error('No proper info found for movie, removing it from library to cause it from having more issues.')
            fireEvent('media.delete', movie['id'], single = True)
            return

        fireEvent('notify.frontend', type = 'movie.searcher.started', data = {'id': movie['id']}, message = 'Searching for "%s"' % default_title)

        db = get_session()

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

                results = fireEvent('searcher.search', search_protocols, movie, quality, single = True) or []
                if len(results) == 0:
                    log.debug('Nothing found for %s in %s', (default_title, quality_type['quality']['label']))

                # Check if movie isn't deleted while searching
                if not db.query(Media).filter_by(id = movie.get('id')).first():
                    break

                # Add them to this movie releases list
                found_releases += fireEvent('release.create_from_search', results, movie, quality_type, single = True)

                # Try find a valid result and download it
                if fireEvent('release.try_download_result', results, movie, quality_type, manual, single = True):
                    ret = True

                # Remove releases that aren't found anymore
                for release in movie.get('releases', []):
                    if release.get('status_id') == available_status.get('id') and release.get('identifier') not in found_releases:
                        fireEvent('release.delete', release.get('id'), single = True)

            else:
                log.info('Better quality (%s) already available or snatched for %s', (quality_type['quality']['label'], default_title))
                fireEvent('media.restatus', movie['id'])
                break

            # Break if CP wants to shut down
            if self.shuttingDown() or ret:
                break

        if len(too_early_to_search) > 0:
            log.info2('Too early to search for %s, %s', (too_early_to_search, default_title))

        fireEvent('notify.frontend', type = 'movie.searcher.ended', data = {'id': movie['id']})

        return ret

    def correctRelease(self, nzb = None, media = None, quality = None, **kwargs):

        if media.get('type') != 'movie': return

        media_title = fireEvent('searcher.get_search_title', media, single = True)

        imdb_results = kwargs.get('imdb_results', False)
        retention = Env.setting('retention', section = 'nzb')

        if nzb.get('seeders') is None and 0 < retention < nzb.get('age', 0):
            log.info2('Wrong: Outside retention, age is %s, needs %s or lower: %s', (nzb['age'], retention, nzb['name']))
            return False

        # Check for required and ignored words
        if not fireEvent('searcher.correct_words', nzb['name'], media, single = True):
            return False

        preferred_quality = fireEvent('quality.single', identifier = quality['identifier'], single = True)

        # Contains lower quality string
        if fireEvent('searcher.contains_other_quality', nzb, movie_year = media['library']['year'], preferred_quality = preferred_quality, single = True):
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
        if getImdb(nzb.get('description', '')) == media['library']['identifier']:
            return True

        for raw_title in media['library']['titles']:
            for movie_title in possibleTitles(raw_title['title']):
                movie_words = re.split('\W+', simplifyString(movie_title))

                if fireEvent('searcher.correct_name', nzb['name'], movie_title, single = True):
                    # if no IMDB link, at least check year range 1
                    if len(movie_words) > 2 and fireEvent('searcher.correct_year', nzb['name'], media['library']['year'], 1, single = True):
                        return True

                    # if no IMDB link, at least check year
                    if len(movie_words) <= 2 and fireEvent('searcher.correct_year', nzb['name'], media['library']['year'], 0, single = True):
                        return True

        log.info("Wrong: %s, undetermined naming. Looking for '%s (%s)'", (nzb['name'], media_title, media['library']['year']))
        return False

    def couldBeReleased(self, is_pre_release, dates, year = None):

        now = int(time.time())
        now_year = date.today().year
        now_month = date.today().month

        if (year is None or year < now_year - 1) and (not dates or (dates.get('theater', 0) == 0 and dates.get('dvd', 0) == 0)):
            return True
        else:

            # Don't allow movies with years to far in the future
            add_year = 1 if now_month > 10 else 0 # Only allow +1 year if end of the year
            if year is not None and year > (now_year + add_year):
                return False

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

    def tryNextRelease(self, media_id, manual = False):

        snatched_status, done_status, ignored_status = fireEvent('status.get', ['snatched', 'done', 'ignored'], single = True)

        try:
            db = get_session()
            rels = db.query(Release) \
                .filter_by(movie_id = media_id) \
                .filter(Release.status_id.in_([snatched_status.get('id'), done_status.get('id')])) \
                .all()

            for rel in rels:
                rel.status_id = ignored_status.get('id')
            db.commit()

            movie_dict = fireEvent('media.get', media_id = media_id, single = True)
            log.info('Trying next release for: %s', getTitle(movie_dict['library']))
            fireEvent('movie.searcher.single', movie_dict, manual = manual)

            return True

        except:
            log.error('Failed searching for next release: %s', traceback.format_exc())
            db.rollback()
            return False
        finally:
            db.close()

    def getSearchTitle(self, media):
        if media['type'] == 'movie':
            return getTitle(media['library'])

class SearchSetupError(Exception):
    pass
