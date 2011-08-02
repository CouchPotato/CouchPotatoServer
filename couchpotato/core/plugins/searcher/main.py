from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Movie
from couchpotato.environment import Env
import re

log = CPLog(__name__)


class Searcher(Plugin):

    def __init__(self):
        addEvent('searcher.all', self.all)
        addEvent('searcher.single', self.single)
        addEvent('searcher.correct_movie', self.correctMovie)

        # Schedule cronjob
        fireEvent('schedule.cron', 'searcher.all', self.all, day = self.conf('cron_day'), hour = self.conf('cron_hour'), minute = self.conf('cron_minute'))
        #addEvent('app.load', self.all)

    def all(self):

        db = get_session()

        movies = db.query(Movie).filter(
            Movie.status.has(identifier = 'active')
        ).all()

        snatched_status = fireEvent('status.get', 'snatched', single = True)

        for movie in movies:
            success = self.single(movie.to_dict(deep = {
                'profile': {'types': {'quality': {}}},
                'releases': {'status': {}, 'quality': {}},
                'library': {'titles': {}, 'files':{}},
                'files': {}
            }))

            # Mark as snatched on success
            if success:
                movie.status_id = snatched_status.get('id')
                db.commit()


    def single(self, movie):

        successful = False
        for type in movie['profile']['types']:

            has_better_quality = False

            # See if beter quality is available
            for release in movie['releases']:
                if release['quality']['order'] <= type['quality']['order']:
                    has_better_quality = True

            # Don't search for quality lower then already available.
            if not has_better_quality:

                log.info('Search for %s in %s' % (movie['library']['titles'][0]['title'], type['quality']['label']))
                results = fireEvent('provider.yarr.search', movie, type['quality'], merge = True)
                sorted_results = sorted(results, key = lambda k: k['score'], reverse = True)

                for nzb in sorted_results:
                    successful = fireEvent('download', data = nzb, single = True)

                    if successful:
                         log.info('Downloading of %s successful.' % nzb.get('name'))
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

        return False

    def containsOtherQuality(self, name, preferred_quality = {}, single_category = False):

        nzb_words = re.split('\W+', simplifyString(name.lower()))
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
        
        if len(found) > 1:
            # Multiple results, let's pick the last one.
            old_results = found.keys()
            old_results.reverse()
            
            for i in old_results:
                log.info(i)
                
                if len(found) > 1:
                    log.info("Remove a redundant quality named %s" % i)
                    found.pop(i)
                    
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
