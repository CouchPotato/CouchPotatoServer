from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import md5
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Movie, Release, ReleaseInfo
from couchpotato.environment import Env
from sqlalchemy.exc import InterfaceError
import re
import traceback

log = CPLog(__name__)


class Searcher(Plugin):

    def __init__(self):
        addEvent('searcher.all', self.all)
        addEvent('searcher.single', self.single)
        addEvent('searcher.correct_movie', self.correctMovie)
        addEvent('searcher.download', self.download)

        # Schedule cronjob
        fireEvent('schedule.cron', 'searcher.all', self.all, day = self.conf('cron_day'), hour = self.conf('cron_hour'), minute = self.conf('cron_minute'))

        if Env.doDebug():
            addEvent('app.load', self.all)

    def all(self):

        db = get_session()

        movies = db.query(Movie).filter(
            Movie.status.has(identifier = 'active')
        ).all()

        for movie in movies:

            self.single(movie.to_dict({
                'profile': {'types': {'quality': {}}},
                'releases': {'status': {}, 'quality': {}},
                'library': {'titles': {}, 'files':{}},
                'files': {}
            }))

            # Break if CP wants to shut down
            if self.shuttingDown():
                break

    def single(self, movie):

        available_status = fireEvent('status.get', 'available', single = True)

        for type in movie['profile']['types']:

            has_better_quality = 0
            default_title = movie['library']['titles'][0]['title']

            # See if beter quality is available
            for release in movie['releases']:
                if release['quality']['order'] <= type['quality']['order'] and release['status_id'] is not available_status.get('id'):
                    has_better_quality += 1

            # Don't search for quality lower then already available.
            if has_better_quality is 0:

                log.info('Search for %s in %s' % (default_title, type['quality']['label']))
                results = fireEvent('yarr.search', movie, type['quality'], merge = True)
                sorted_results = sorted(results, key = lambda k: k['score'], reverse = True)

                # Add them to this movie releases list
                for nzb in sorted_results:
                    db = get_session()

                    rls = db.query(Release).filter_by(identifier = md5(nzb['url'])).first()
                    if not rls:
                        rls = Release(
                            identifier = md5(nzb['url']),
                            movie_id = movie.get('id'),
                            quality_id = type.get('quality_id'),
                            status_id = available_status.get('id')
                        )
                        db.add(rls)
                        db.commit()

                        for info in nzb:
                            try:
                                if not isinstance(nzb[info], (str, unicode, int, long)):
                                    continue

                                rls_info = ReleaseInfo(
                                    identifier = info,
                                    value = nzb[info]
                                )
                                rls.info.append(rls_info)
                                db.commit()
                            except InterfaceError:
                                log.debug('Couldn\'t add %s to ReleaseInfo: %s' % (info, traceback.format_exc()))


                for nzb in sorted_results:
                    return self.download(data = nzb, movie = movie)
            else:
                log.info('Better quality (%s) already available or snatched for %s' % (type['quality']['label'], default_title))
                break

            # Break if CP wants to shut down
            if self.shuttingDown():
                break

        return False

    def download(self, data, movie):

        snatched_status = fireEvent('status.get', 'snatched', single = True)

        successful = fireEvent('download', data = data, movie = movie, single = True)

        if successful:

            # Mark release as snatched
            db = get_session()
            rls = db.query(Release).filter_by(identifier = md5(data['url'])).first()
            rls.status_id = snatched_status.get('id')
            db.commit()

            log.info('Downloading of %s successful.' % data.get('name'))
            fireEvent('movie.snatched', message = 'Downloading of %s successful.' % data.get('name'), data = rls.to_dict())

            return True

        return False

    def correctMovie(self, nzb = {}, movie = {}, quality = {}, **kwargs):

        imdb_results = kwargs.get('imdb_results', False)
        single_category = kwargs.get('single_category', False)
        retention = Env.setting('retention', section = 'nzb')

        if retention < nzb.get('age', 0):
            log.info('Wrong: Outside retention, age is %s, needs %s or lower: %s' % (nzb['age'], retention, nzb['name']))
            return False

        nzb_words = re.split('\W+', simplifyString(nzb['name']))
        required_words = self.conf('required_words').split(',')

        if self.conf('required_words') and not list(set(nzb_words) & set(required_words)):
            log.info("NZB doesn't contain any of the required words.")
            return False

        ignored_words = self.conf('ignored_words').split(',')
        blacklisted = list(set(nzb_words) & set(ignored_words))
        if self.conf('ignored_words') and blacklisted:
            log.info("Wrong: '%s' blacklisted words: %s" % (nzb['name'], ", ".join(blacklisted)))
            return False

        #qualities = fireEvent('quality.all', single = True)
        preferred_quality = fireEvent('quality.single', identifier = quality['identifier'], single = True)

        # Contains lower quality string
        if self.containsOtherQuality(nzb['name'], preferred_quality, single_category):
            log.info('Wrong: %s, looking for %s' % (nzb['name'], quality['label']))
            return False

        """
        # File to small
        minSize = q.minimumSize(qualityType)
        if minSize > item.size:
            log.info('"%s" is too small to be %s. %sMB instead of the minimal of %sMB.' % (item.name, type['label'], item.size, minSize))
            return False

        # File to large
        maxSize = q.maximumSize(qualityType)
        if maxSize < item.size:
            log.info('"%s" is too large to be %s. %sMB instead of the maximum of %sMB.' % (item.name, type['label'], item.size, maxSize))
            return False

        """

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
                if len(movie_words) == 2 and self.correctYear([nzb['name']], movie['library']['year'], 0):
                    return True

        # Get the nfo and see if it contains the proper imdb url
        if self.checkNFO(nzb['name'], movie['library']['identifier']):
            return True

        log.info("Wrong: %s, undetermined naming. Looking for '%s (%s)'" % (nzb['name'], movie['library']['titles'][0]['title'], movie['library']['year']))
        return False

    def containsOtherQuality(self, name, preferred_quality = {}, single_category = False):

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

        # Allow other qualities
        for allowed in preferred_quality.get('allow'):
            if found.get(allowed):
                del found[allowed]

        if (len(found) == 0 and single_category):
            return False

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

        check_words = re.split('\W+', simplifyString(check_name))
        movie_words = re.split('\W+', simplifyString(movie_name))

        return len(list(set(check_words) & set(movie_words))) == len(movie_words)

    def checkNFO(self, releasename, imdbId):
        nfo = self.urlopen('http://www.srrdb.com/showfile.php?release='+releasename)
        nfo = nfo.decode('iso-8859-1').encode('ascii', 'ignore')
        if 'imdb.com/title/' + imdbId in nfo:
            return True 
        return False