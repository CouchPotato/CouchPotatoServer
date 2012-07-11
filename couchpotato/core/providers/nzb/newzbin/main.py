from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from dateutil.parser import parse
import base64
import time
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class Newzbin(NZBProvider, RSS):

    urls = {
        'download': 'https://www.newzbin2.es/api/dnzb/',
        'search': 'https://www.newzbin2.es/search/',
    }

    format_ids = {
        2: ['scr'],
        1: ['cam'],
        4: ['tc'],
        8: ['ts'],
        1024: ['r5'],
    }
    cat_ids = [
        ([262144], ['bd50']),
        ([2097152], ['1080p']),
        ([524288], ['720p']),
        ([262144], ['brrip']),
        ([2], ['dvdr']),
    ]
    cat_backup_id = -1

    http_time_between_calls = 3 # Seconds

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        format_id = self.getFormatId(type)
        cat_id = self.getCatId(type)

        arguments = tryUrlencode({
            'searchaction': 'Search',
            'u_url_posts_only': '0',
            'u_show_passworded': '0',
            'q_url': 'imdb.com/title/' + movie['library']['identifier'],
            'sort': 'ps_totalsize',
            'order': 'asc',
            'u_post_results_amt': '100',
            'feed': 'rss',
            'category': '6',
            'ps_rb_video_format': str(cat_id),
            'ps_rb_source': str(format_id),
            'u_post_larger_than': quality.get('size_min'),
            'u_post_smaller_than': quality.get('size_max'),
        })

        url = "%s?%s" % (self.urls['search'], arguments)
        cache_key = str('newzbin.%s.%s.%s' % (movie['library']['identifier'], str(format_id), str(cat_id)))

        data = self.getCache(cache_key)
        if not data:

            headers = {
                'Authorization': "Basic %s" % base64.encodestring('%s:%s' % (self.conf('username'), self.conf('password')))[:-1]
            }
            try:
                data = self.urlopen(url, headers = headers)
                self.setCache(cache_key, data)
            except:
                return results

        if data:
            try:
                try:
                    data = XMLTree.fromstring(data)
                    nzbs = self.getElements(data, 'channel/item')
                except Exception, e:
                    log.debug('%s, %s', (self.getName(), e))
                    return results

                for nzb in nzbs:

                    title = self.getTextElement(nzb, "title")
                    if 'error' in title.lower(): continue

                    REPORT_NS = 'http://www.newzbin2.es/DTD/2007/feeds/report/';

                    # Add attributes to name
                    try:
                        for attr in nzb.find('{%s}attributes' % REPORT_NS):
                            title += ' ' + attr.text
                    except:
                        pass

                    id = int(self.getTextElement(nzb, '{%s}id' % REPORT_NS))
                    size = str(int(self.getTextElement(nzb, '{%s}size' % REPORT_NS)) / 1024 / 1024) + ' mb'
                    date = str(self.getTextElement(nzb, '{%s}postdate' % REPORT_NS))

                    new = {
                        'id': id,
                        'type': 'nzb',
                        'provider': self.getName(),
                        'name': title,
                        'age': self.calculateAge(int(time.mktime(parse(date).timetuple()))),
                        'size': self.parseSize(size),
                        'url': str(self.getTextElement(nzb, '{%s}nzb' % REPORT_NS)),
                        'download': self.download,
                        'detail_url': str(self.getTextElement(nzb, 'link')),
                        'description': self.getTextElement(nzb, "description"),
                        'check_nzb': False,
                    }

                    is_correct_movie = fireEvent('searcher.correct_movie',
                                                 nzb = new, movie = movie, quality = quality,
                                                 imdb_results = True, single = True)
                    if is_correct_movie:
                        new['score'] = fireEvent('score.calculate', new, movie, single = True)
                        results.append(new)
                        self.found(new)

                return results
            except SyntaxError:
                log.error('Failed to parse XML response from newzbin')

        return results

    def download(self, url = '', nzb_id = ''):
        try:
            log.info('Download nzb from newzbin, report id: %s ', nzb_id)

            return self.urlopen(self.urls['download'], params = {
                'username' : self.conf('username'),
                'password' : self.conf('password'),
                'reportid' : nzb_id
            }, show_error = False)
        except Exception, e:
            log.error('Failed downloading from newzbin, check credit: %s', e)
            return False

    def getFormatId(self, format):
        for id, quality in self.format_ids.iteritems():
            for q in quality:
                if q == format:
                    return id

        return self.cat_backup_id

    def isEnabled(self):
        return NZBProvider.isEnabled(self) and self.conf('enabled') and self.conf('username') and self.conf('password')
