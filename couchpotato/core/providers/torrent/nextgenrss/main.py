from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
from urlparse import parse_qs
import traceback


log = CPLog(__name__)


class NextGenRSS(TorrentProvider):

    urls = {
        'test' : 'https://nxtgn.org',
        'detail' : 'https://nxtgn.org/details.php?id=%s',
    }

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def _searchOnTitle(self, title, movie, quality, results):

        url = self.conf('rssurl')
        data = self.getHTMLData(url)

        if data:
            html = BeautifulSoup(data)

            try:
                entries = html.find_all('item')

                for result in entries:

                    titlefromrss2 = (result.find('title').text).replace('and','&')
					
                    titlefromrss3 = titlefromrss2.replace('EXTENDED','')
                    titlefromrss = titlefromrss3.replace('Unrated.Cut','')
                    

                    link = result.find('link').nextSibling
                    link = link[:link.find('\n')]
                    
                    description = result.find('description').text

                    size = description[:description.find('\n Desc')]
                    size = size[description.find('Size: '):]
                    size = size.replace('Size:', '')
                    size = size.strip()

                    id = link[link.find('id='):]
                    id = id[:id.find('&rss')]
                    id = id.replace('id=', '')
   
                    detailurl = self.urls['detail'] % id

                    results.append({
                        'id': id,
                        'name': titlefromrss,
                        'url': link,
                        'detail_url': detailurl,
                    })


            except:
                log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))
