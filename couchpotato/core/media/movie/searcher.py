from datetime import date
import random
import re
import time
import traceback

from couchpotato import get_db
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.variable import getTitle, possibleTitles, getImdb, getIdentifier, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.searcher.base import SearcherBase
from couchpotato.core.media.movie import MovieTypeBase
from couchpotato.environment import Env


log = CPLog(__name__)

autoload = 'MovieSearcher'


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
                'media_id': {'desc': 'The id of the media'},
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
            def on_load():
                time.sleep(.1)
                self.searchAll()
            addEvent('app.load', on_load, priority = 1000)

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

        medias = [x['_id'] for x in fireEvent('media.with_status', 'active', with_doc = False, single = True)]
        random.shuffle(medias)

        total = len(medias)
        self.in_progress = {
            'total': total,
            'to_go': total,
        }

        try:
            search_protocols = fireEvent('searcher.protocols', single = True)

            for media_id in medias:

                media = fireEvent('media.get', media_id, single = True)

                try:
                    self.single(media, search_protocols)
                except IndexError:
                    log.error('Forcing library update for %s, if you see this often, please report: %s', (getIdentifier(media), traceback.format_exc()))
                    fireEvent('movie.update_info', media_id)
                except:
                    log.error('Search failed for %s: %s', (getIdentifier(media), traceback.format_exc()))

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

        if not movie['profile_id'] or (movie['status'] == 'done' and not manual):
            log.debug('Movie doesn\'t have a profile or already done, assuming in manage tab.')
            return

        pre_releases = fireEvent('quality.pre_releases', single = True)
        release_dates = fireEvent('movie.update_release_dates', movie['_id'], merge = True)

        found_releases = []
        previous_releases = movie.get('releases', [])
        too_early_to_search = []

        default_title = getTitle(movie)
        if not default_title:
            log.error('No proper info found for movie, removing it from library to cause it from having more issues.')
            fireEvent('media.delete', movie['_id'], single = True)
            return

        fireEvent('notify.frontend', type = 'movie.searcher.started', data = {'_id': movie['_id']}, message = 'Searching for "%s"' % default_title)

        db = get_db()

        profile = db.get('id', movie['profile_id'])
        ret = False

        index = 0
        for q_identifier in profile.get('qualities'):
            quality_custom = {
                'index': index,
                'quality': q_identifier,
                'finish': profile['finish'][index],
                'wait_for': tryInt(profile['wait_for'][index]),
                '3d': profile['3d'][index] if profile.get('3d') else False
            }

            index += 1

            if not self.conf('always_search') and not self.couldBeReleased(q_identifier in pre_releases, release_dates, movie['info']['year']):
                too_early_to_search.append(q_identifier)
                continue

            has_better_quality = 0

            # See if better quality is available
            for release in movie.get('releases', []):
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
                fireEvent('media.restatus', movie['_id'])
                break

            quality = fireEvent('quality.single', identifier = q_identifier, single = True)
            log.info('Search for %s in %s', (default_title, quality['label']))

            # Extend quality with profile customs
            quality['custom'] = quality_custom

            results = fireEvent('searcher.search', search_protocols, movie, quality, single = True) or []
            if len(results) == 0:
                log.debug('Nothing found for %s in %s', (default_title, quality['label']))

            # Check if movie isn't deleted while searching
            if not fireEvent('media.get', movie.get('_id'), single = True):
                break

            # Add them to this movie releases list
            found_releases += fireEvent('release.create_from_search', results, movie, quality, single = True)

            # Try find a valid result and download it
            if fireEvent('release.try_download_result', results, movie, quality_custom, manual, single = True):
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

        if len(too_early_to_search) > 0:
            log.info2('Too early to search for %s, %s', (too_early_to_search, default_title))

        fireEvent('notify.frontend', type = 'movie.searcher.ended', data = {'_id': movie['_id']})

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

        preferred_quality = quality if quality else fireEvent('quality.single', identifier = quality['identifier'], single = True)

        # Contains lower quality string
        contains_other = fireEvent('searcher.contains_other_quality', nzb, movie_year = media['info']['year'], preferred_quality = preferred_quality, single = True)
        if contains_other != False:
            log.info2('Wrong: %s, looking for %s, found %s', (nzb['name'], quality['label'], [x for x in contains_other] if contains_other else 'no quality'))
            return False

        # Contains lower quality string
        if not fireEvent('searcher.correct_3d', nzb, preferred_quality = preferred_quality, single = True):
            log.info2('Wrong: %s, %slooking for %s in 3D', (nzb['name'], ('' if preferred_quality['custom'].get('3d') else 'NOT '), quality['label']))
            return False

        # File to small
        if nzb['size'] and tryInt(preferred_quality['size_min']) > tryInt(nzb['size']):
            log.info2('Wrong: "%s" is too small to be %s. %sMB instead of the minimal of %sMB.', (nzb['name'], preferred_quality['label'], nzb['size'], preferred_quality['size_min']))
            return False

        # File to large
        if nzb['size'] and tryInt(preferred_quality['size_max']) < tryInt(nzb['size']):
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
        if getImdb(nzb.get('description', '')) == getIdentifier(media):
            return True

        for raw_title in media['info']['titles']:
            for movie_title in possibleTitles(raw_title):
                movie_words = re.split('\W+', simplifyString(movie_title))

                if fireEvent('searcher.correct_name', nzb['name'], movie_title, single = True):
                    # if no IMDB link, at least check year range 1
                    if len(movie_words) > 2 and fireEvent('searcher.correct_year', nzb['name'], media['info']['year'], 1, single = True):
                        return True

                    # if no IMDB link, at least check year
                    if len(movie_words) <= 2 and fireEvent('searcher.correct_year', nzb['name'], media['info']['year'], 0, single = True):
                        return True

        log.info("Wrong: %s, undetermined naming. Looking for '%s (%s)'", (nzb['name'], media_title, media['info']['year']))
        return False

    def couldBeReleased(self, is_pre_release, dates, year = None):

        now = int(time.time())
        now_year = date.today().year
        now_month = date.today().month

        if (year is None or year < now_year - 1 or (year <= now_year - 1 and now_month > 4)) and (not dates or (dates.get('theater', 0) == 0 and dates.get('dvd', 0) == 0)):
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

    def tryNextReleaseView(self, media_id = None, **kwargs):

        trynext = self.tryNextRelease(media_id, manual = True)

        return {
            'success': trynext
        }

    def tryNextRelease(self, media_id, manual = False):

        try:
            db = get_db()
            rels = fireEvent('media.with_status', ['snatched', 'done'], single = True)

            for rel in rels:
                rel['status'] = 'ignored'
                db.update(rel)

            movie_dict = fireEvent('media.get', media_id, single = True)
            log.info('Trying next release for: %s', getTitle(movie_dict))
            self.single(movie_dict, manual = manual)

            return True

        except:
            log.error('Failed searching for next release: %s', traceback.format_exc())
            return False

    def getSearchTitle(self, media):
        if media['type'] == 'movie':
            return getTitle(media)

class SearchSetupError(Exception):
    pass


config = [{
    'name': 'moviesearcher',
    'order': 20,
    'groups': [
        {
            'tab': 'searcher',
            'name': 'movie_searcher',
            'label': 'Movie search',
            'description': 'Search options for movies',
            'advanced': True,
            'options': [
                {
                    'name': 'always_search',
                    'default': False,
                    'migrate_from': 'searcher',
                    'type': 'bool',
                    'label': 'Always search',
                    'description': 'Search for movies even before there is a ETA. Enabling this will probably get you a lot of fakes.',
                },
                {
                    'name': 'run_on_launch',
                    'migrate_from': 'searcher',
                    'label': 'Run on launch',
                    'advanced': True,
                    'default': 0,
                    'type': 'bool',
                    'description': 'Force run the searcher after (re)start.',
                },
                {
                    'name': 'search_on_add',
                    'label': 'Search after add',
                    'advanced': True,
                    'default': 1,
                    'type': 'bool',
                    'description': 'Disable this to only search for movies on cron.',
                },
                {
                    'name': 'cron_day',
                    'migrate_from': 'searcher',
                    'label': 'Day',
                    'advanced': True,
                    'default': '*',
                    'type': 'string',
                    'description': '<strong>*</strong>: Every day, <strong>*/2</strong>: Every 2 days, <strong>1</strong>: Every first of the month. See <a href="http://packages.python.org/APScheduler/cronschedule.html">APScheduler</a> for details.',
                },
                {
                    'name': 'cron_hour',
                    'migrate_from': 'searcher',
                    'label': 'Hour',
                    'advanced': True,
                    'default': random.randint(0, 23),
                    'type': 'string',
                    'description': '<strong>*</strong>: Every hour, <strong>*/8</strong>: Every 8 hours, <strong>3</strong>: At 3, midnight.',
                },
                {
                    'name': 'cron_minute',
                    'migrate_from': 'searcher',
                    'label': 'Minute',
                    'advanced': True,
                    'default': random.randint(0, 59),
                    'type': 'string',
                    'description': "Just keep it random, so the providers don't get DDOSed by every CP user on a 'full' hour."
                },
            ],
        },
    ],
}]
