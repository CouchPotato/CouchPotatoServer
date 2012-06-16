from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode, \
    simplifyString
from couchpotato.core.helpers.variable import tryInt, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env

log = CPLog(__name__)


class Mysterbin(NZBProvider):

    urls = {
        'search': 'https://www.mysterbin.com/advsearch?%s',
        'download': 'https://www.mysterbin.com/nzb?c=%s',
        'nfo': 'https://www.mysterbin.com/nfo?c=%s',
    }

    http_time_between_calls = 1 #seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        q = '"%s" %s %s' % (simplifyString(getTitle(movie['library'])), movie['library']['year'], quality.get('identifier'))
        for ignored in Env.setting('ignored_words', 'searcher').split(','):
            if len(q) + len(ignored.strip()) > 126:
                break
            q = '%s -%s' % (q, ignored.strip())

        params = {
            'q': q,
            'match': 'normal',
            'minSize': quality.get('size_min'),
            'maxSize': quality.get('size_max'),
            'complete': 2,
            'maxAge': Env.setting('retention', 'nzb'),
            'nopasswd': 'on',
        }

        cache_key = 'mysterbin.%s.%s.%s' % (movie['library']['identifier'], quality.get('identifier'), q)
        data = self.getCache(cache_key, self.urls['search'] % tryUrlencode(params))
        if data:

            try:
                html = BeautifulSoup(data)
                resultable = html.find('table', attrs = {'class':'t'})
                for result in resultable.find_all('tr'):

                    try:
                        myster_id = result.find('input', attrs = {'class': 'check4nzb'})['value']

                        # Age
                        age = ''
                        for temp in result.find('td', attrs = {'class': 'cdetail'}).find_all(text = True):
                            if 'days' in temp:
                                age = tryInt(temp.split(' ')[0])
                                break

                        # size
                        size = None
                        for temp in result.find('div', attrs = {'class': 'cdetail'}).find_all(text = True):
                            if 'gb' in temp.lower() or 'mb' in temp.lower() or 'kb' in temp.lower():
                                size = self.parseSize(temp)
                                break

                        description = ''
                        if result.find('a', text = 'View NFO'):
                            description = toUnicode(self.getCache('mysterbin.%s' % myster_id, self.urls['nfo'] % myster_id, cache_timeout = 25920000))

                        new = {
                            'id': myster_id,
                            'name': ''.join(result.find('span', attrs = {'class': 'cname'}).find_all(text = True)),
                            'type': 'nzb',
                            'provider': self.getName(),
                            'age': age,
                            'size': size,
                            'url': self.urls['download'] % myster_id,
                            'description': description,
                            'download': self.download,
                            'check_nzb': False,
                        }

                        new['score'] = fireEvent('score.calculate', new, movie, single = True)
                        is_correct_movie = fireEvent('searcher.correct_movie',
                                                        nzb = new, movie = movie, quality = quality,
                                                        imdb_results = False, single_category = False, single = True)
                        if is_correct_movie:
                            results.append(new)
                            self.found(new)
                    except:
                        pass

                return results
            except AttributeError:
                log.debug('No search results found.')

        return results
