from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from dateutil.parser import parse
import time

log = CPLog(__name__)


class NZBto(NZBProvider, RSS):

    urls = {
        'search': '?',
    }

    http_time_between_calls = 10  #seconds

    def _searchOnTitle(self, title, movie, quality, results):
        host = str(self.conf('proxy'))
        
        q = '%s %s' % (title, movie['library']['year'])

        q_param = tryUrlencode({
			'mode': 'search'
        })

        params = tryUrlencode({
            'user' : self.conf('nzbto_username'),
            'pass' : self.conf('nzbto_password'),
            'title': q
        })
		
        url = '%s?%s&%s' % (host, q_param, params)
        nzbs = self.getRSSData(url)

        for nzb in nzbs:

            enclosure = self.getElement(nzb, "enclosure").attrib
            nzbto_id  = enclosure['id']
            size      = enclosure['length']
            date      = self.getTextElement(nzb, "pubDate")
            
            dlparamsmode = tryUrlencode({
            	'mode' : 'nzb',
            })

            dlnamemode = tryUrlencode({
                'mode' : 'name',
            })
            
            dlparams = tryUrlencode({
            	'user' : self.conf('nzbto_username'),
				'pass' : self.conf('nzbto_password'),
				'nid' : nzbto_id,
			})

            def extra_check(item):
                full_description = self.getCache('nzbto.%s' % nzbto_id, item['detail_url'], cache_timeout = 25920000)

                for ignored in ['ARCHIVE inside ARCHIVE', 'Incomplete', 'repair impossible']:
                    if ignored in full_description:
                        log.info('Wrong: Seems to be passworded or corrupted files: %s', item['name'])
                        return False

                return True


            dlurl = '%s?%s&%s' % (host, dlparamsmode, dlparams)
            nameurl = '%s?%s&%s' % (host, dlnamemode, dlparams)
            
            results.append({
                'id': nzbto_id,
                'name': toUnicode(self.getTextElement(nzb, "title")),
                'age': self.calculateAge(int(time.mktime(parse(date).timetuple()))),
                'size': tryInt(size) / 1024 / 1024,
                'url': dlurl,
                'nameurl': nameurl,
                'detail_url': self.getTextElement(nzb, "link")
                #'get_more_info': self.getMoreInfo,
                #'extra_check': extra_check
            })

    def getMoreInfo(self, item):
        full_description = self.getCache('nzbto.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('pre', attrs = {'class':'nfo'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

    def extraCheck(self, item):
        full_description = self.getCache('nzbto.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)

        if 'ARCHIVE inside ARCHIVE' in full_description:
            log.info('Wrong: Seems to be passworded files: %s', item['name'])
            return False

        return True
