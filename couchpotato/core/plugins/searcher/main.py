from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.helpers.request import jsonified, getParam
from couchpotato.core.helpers.variable import md5, getImdb, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Movie, Release, ReleaseInfo
from couchpotato.environment import Env
from inspect import ismethod, isfunction
from sqlalchemy.exc import InterfaceError
import datetime
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
        addEvent('searcher.check_snatched', self.checkSnatched)

        addApiView('searcher.try_next', self.tryNextReleaseView, docs = {
            'desc': 'Marks the snatched results as ignored and try the next best release',
            'params': {
                'id': {'desc': 'The id of the movie'},
            },
        })

        # Schedule cronjob
        fireEvent('schedule.cron', 'searcher.all', self.allMovies, day = self.conf('cron_day'), hour = self.conf('cron_hour'), minute = self.conf('cron_minute'))
        fireEvent('schedule.interval', 'searcher.check_snatched', self.checkSnatched, minutes = self.conf('run_every'))


    def allMovies(self):

        if self.in_progress:
            log.info('Search already in progress')
            return

        self.in_progress = True

        db = get_session()

        movies = db.query(Movie).filter(
            Movie.status.has(identifier = 'active')
        ).all()

        for movie in movies:
            movie_dict = movie.to_dict({
                'profile': {'types': {'quality': {}}},
                'releases': {'status': {}, 'quality': {}},
                'library': {'titles': {}, 'files':{}},
                'files': {}
            })

            try:
                self.single(movie_dict)
            except IndexError:
                fireEvent('library.update', movie_dict['library']['identifier'], force = True)
            except:
                log.error('Search failed for %s: %s', (movie_dict['library']['identifier'], traceback.format_exc()))

            # Break if CP wants to shut down
            if self.shuttingDown():
                break

        #db.close()
        self.in_progress = False

    def single(self, movie):

        done_status = fireEvent('status.get', 'done', single = True)

        if not movie['profile'] or movie['status_id'] == done_status.get('id'):
            log.debug('Movie doesn\'t have a profile or already done, assuming in manage tab.')
            return

        db = get_session()

        pre_releases = fireEvent('quality.pre_releases', single = True)
        release_dates = fireEvent('library.update_release_date', identifier = movie['library']['identifier'], merge = True)
        available_status = fireEvent('status.get', 'available', single = True)
        ignored_status = fireEvent('status.get', 'ignored', single = True)

        default_title = getTitle(movie['library'])
        if not default_title:
            return

        fireEvent('notify.frontend', type = 'searcher.started.%s' % movie['id'], data = True, message = 'Searching for "%s"' % default_title)

        ret = False
        for quality_type in movie['profile']['types']:
            if not self.couldBeReleased(quality_type['quality']['identifier'], release_dates, pre_releases):
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

                results = fireEvent('yarr.search', movie, quality, merge = True)

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

                    rls = db.query(Release).filter_by(identifier = md5(nzb['url'])).first()
                    if not rls:
                        rls = Release(
                            identifier = md5(nzb['url']),
                            movie_id = movie.get('id'),
                            quality_id = quality_type.get('quality_id'),
                            status_id = available_status.get('id')
                        )
                        db.add(rls)
                        db.commit()
                    else:
                        [db.delete(info) for info in rls.info]
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
                            db.commit()
                        except InterfaceError:
                            log.debug('Couldn\'t add %s to ReleaseInfo: %s', (info, traceback.format_exc()))

                    nzb['status_id'] = rls.status_id


                for nzb in sorted_results:
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
            else:
                log.info('Better quality (%s) already available or snatched for %s', (quality_type['quality']['label'], default_title))
                fireEvent('movie.restatus', movie['id'])
                break

            # Break if CP wants to shut down
            if self.shuttingDown() or ret:
                break

        fireEvent('notify.frontend', type = 'searcher.ended.%s' % movie['id'], data = True)

        #db.close()
        return ret

    def download(self, data, movie, manual = False):

        snatched_status = fireEvent('status.get', 'snatched', single = True)

        # Download movie to temp
        filedata = None
        if data.get('download') and (ismethod(data.get('download')) or isfunction(data.get('download'))):
            filedata = data.get('download')(url = data.get('url'), nzb_id = data.get('id'))
            if filedata is 'try_next':
                return filedata

        successful = fireEvent('download', data = data, movie = movie, manual = manual, filedata = filedata, single = True)

        if successful:

            # Mark release as snatched
            db = get_session()
            rls = db.query(Release).filter_by(identifier = md5(data['url'])).first()
            rls.status_id = snatched_status.get('id')
            db.commit()

            log_movie = '%s (%s) in %s' % (getTitle(movie['library']), movie['library']['year'], rls.quality.label)
            snatch_message = 'Snatched "%s": %s' % (data.get('name'), log_movie)
            log.info(snatch_message)
            fireEvent('movie.snatched', message = snatch_message, data = rls.to_dict())


            # If renamer isn't used, mark movie done
            if not Env.setting('enabled', 'renamer'):
                active_status = fireEvent('status.get', 'active', single = True)
                done_status = fireEvent('status.get', 'done', single = True)
                try:
                    if movie['status_id'] == active_status.get('id'):
                        for profile_type in movie['profile']['types']:
                            if profile_type['quality_id'] == rls.quality.id and profile_type['finish']:
                                log.info('Renamer disabled, marking movie as finished: %s', log_movie)

                                # Mark release done
                                rls.status_id = done_status.get('id')
                                db.commit()

                                # Mark movie done
                                mvie = db.query(Movie).filter_by(id = movie['id']).first()
                                mvie.status_id = done_status.get('id')
                                db.commit()
                except Exception, e:
                    log.error('Failed marking movie finished: %s %s', (e, traceback.format_exc()))

            #db.close()
            return True

        log.info('Tried to download, but none of the downloaders are enabled')
        return False

    def correctMovie(self, nzb = {}, movie = {}, quality = {}, **kwargs):

        imdb_results = kwargs.get('imdb_results', False)
        retention = Env.setting('retention', section = 'nzb')

        if nzb.get('seeds') is None and retention < nzb.get('age', 0):
            log.info('Wrong: Outside retention, age is %s, needs %s or lower: %s', (nzb['age'], retention, nzb['name']))
            return False

        movie_name = getTitle(movie['library'])
        movie_words = re.split('\W+', simplifyString(movie_name))
        nzb_name = simplifyString(nzb['name'])
        nzb_words = re.split('\W+', nzb_name)
        required_words = [x.strip().lower() for x in self.conf('required_words').lower().split(',')]

        if self.conf('required_words') and not list(set(nzb_words) & set(required_words)):
            log.info("Wrong: Required word missing: %s" % nzb['name'])
            return False

        ignored_words = [x.strip().lower() for x in self.conf('ignored_words').split(',')]
        blacklisted = list(set(nzb_words) & set(ignored_words))
        if self.conf('ignored_words') and blacklisted:
            log.info("Wrong: '%s' blacklisted words: %s" % (nzb['name'], ", ".join(blacklisted)))
            return False

        pron_tags = ['xxx', 'sex', 'anal', 'tits', 'fuck', 'porn', 'orgy', 'milf', 'boobs', 'erotica', 'erotic']
        for p_tag in pron_tags:
            if p_tag in nzb_words and p_tag not in movie_words:
                log.info('Wrong: %s, probably pr0n', (nzb['name']))
                return False

        #qualities = fireEvent('quality.all', single = True)
        preferred_quality = fireEvent('quality.single', identifier = quality['identifier'], single = True)

        # Contains lower quality string
        if self.containsOtherQuality(nzb, movie_year = movie['library']['year'], preferred_quality = preferred_quality):
            log.info('Wrong: %s, looking for %s', (nzb['name'], quality['label']))
            return False


        # File to small
        if nzb['size'] and preferred_quality['size_min'] > nzb['size']:
            log.info('"%s" is too small to be %s. %sMB instead of the minimal of %sMB.', (nzb['name'], preferred_quality['label'], nzb['size'], preferred_quality['size_min']))
            return False

        # File to large
        if nzb['size'] and preferred_quality.get('size_max') < nzb['size']:
            log.info('"%s" is too large to be %s. %sMB instead of the maximum of %sMB.', (nzb['name'], preferred_quality['label'], nzb['size'], preferred_quality['size_max']))
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
        if self.checkIMDB([nzb['description']], movie['library']['identifier']):
            return True

        for movie_title in movie['library']['titles']:
            movie_words = re.split('\W+', simplifyString(movie_title['title']))

            if self.correctName(nzb['name'], movie_title['title']):
                # if no IMDB link, at least check year range 1
                if len(movie_words) > 2 and self.correctYear([nzb['name']], movie['library']['year'], 1):
                    return True

                # if no IMDB link, at least check year
                if len(movie_words) <= 2 and self.correctYear([nzb['name']], movie['library']['year'], 0):
                    return True

        # Get the nfo and see if it contains the proper imdb url
        if self.checkNFO(nzb['name'], movie['library']['identifier']):
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

        # Hack for older movies that don't contain quality tag
        year_name = fireEvent('scanner.name_year', name, single = True)
        if movie_year < datetime.datetime.now().year - 3 and not year_name.get('year', None):
            if size > 3000: # Assume dvdr
                return 'dvdr' == preferred_quality['identifier']
            else: # Assume dvdrip
                return 'dvdrip' == preferred_quality['identifier']

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

    def correctYear(self, haystack, year, range):

        for string in haystack:
            if str(year) in string or str(int(year) + range) in string or str(int(year) - range) in string: # 1 year of is fine too
                return True

        return False

    def correctName(self, check_name, movie_name):

        check_names = [check_name]
        try:
            check_names.append(re.search(r'([\'"])[^\1]*\1', check_name).group(0))
        except:
            pass

        for check_name in check_names:
            check_movie = fireEvent('scanner.name_year', check_name, single = True)

            try:
                check_words = filter(None, re.split('\W+', check_movie.get('name', '')))
                movie_words = filter(None, re.split('\W+', simplifyString(movie_name)))

                if len(check_words) > 0 and len(movie_words) > 0 and len(list(set(check_words) - set(movie_words))) == 0:
                    return True
            except:
                pass

        return False

    def checkNFO(self, check_name, imdb_id):
        cache_key = 'srrdb.com %s' % simplifyString(check_name)

        nfo = self.getCache(cache_key)
        if not nfo:
            try:
                nfo = self.urlopen('http://www.srrdb.com/showfile.php?release=%s' % check_name, show_error = False)
                self.setCache(cache_key, nfo)
            except:
                pass

        return nfo and getImdb(nfo) == imdb_id

    def couldBeReleased(self, wanted_quality, dates, pre_releases):

        now = int(time.time())

        if not dates or (dates.get('theater', 0) == 0 and dates.get('dvd', 0) == 0):
            return True
        else:
            if wanted_quality in pre_releases:
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

    def checkSnatched(self):
        snatched_status = fireEvent('status.get', 'snatched', single = True)
        ignored_status = fireEvent('status.get', 'ignored', single = True)
        failed_status = fireEvent('status.get', 'failed', single = True)

        done_status = fireEvent('status.get', 'done', single = True)

        db = get_session()
        rels = db.query(Release).filter_by(status_id = snatched_status.get('id'))

        if rels:
            log.debug('Checking status snatched releases...')

        scanrequired = False

        for rel in rels:

            # Get current selected title
            default_title = ''
            for title in rel.movie.library.titles:
                if title.default: default_title = title.title

            log.debug('Checking snatched movie: %s' , default_title)

            # Check if movie has already completed and is manage tab (legacy db correction)
            if rel.movie.status_id == done_status.get('id'):
                log.debug('Found a completed movie with a snatched release : %s. Setting release status to ignored...' , default_title)
                rel.status_id = ignored_status.get('id')
                db.commit()
                continue

            item = {}
            for info in rel.info:
                item[info.identifier] = info.value

            movie_dict = fireEvent('movie.get', rel.movie_id, single = True)

            # check status
            downloadstatus = fireEvent('download.status', data = item, movie = movie_dict, single = True)
            if not downloadstatus:
                log.debug('Download status functionality is not implemented for active downloaders.')
                scanrequired = True
            else:
                log.debug('Download status: %s' , downloadstatus)

                if downloadstatus == 'failed':
                    if self.conf('next_on_failed'):
                        self.tryNextRelease(rel.movie_id)
                    else:
                        rel.status_id = failed_status.get('id')
                        db.commit()

                        log.info('Download of %s failed.', item['name'])

                elif downloadstatus == 'completed':
                    log.info('Download of %s completed!', item['name'])
                    scanrequired = True

                elif downloadstatus == 'not_found':
                    log.info('%s not found in downloaders', item['name'])
                    rel.status_id = ignored_status.get('id')
                    db.commit()

        # Note that Queued, Downloading, Paused, Repair and Unpackimg are also available as status for SabNZBd
        if scanrequired:
            fireEvent('renamer.scan')

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
