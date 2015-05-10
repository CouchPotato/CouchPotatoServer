import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.kickasstorrents import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'KickAssTorrents'


class KickAssTorrents(MovieProvider, Base):

    urls = {
        'detail': '%s/%s',
        'search': '%s/%s-i%s/',
    }

    cat_ids = [
        (['cam'], ['cam']),
        (['telesync'], ['ts', 'tc']),
        (['screener', 'tvrip'], ['screener']),
        (['x264', '720p', '1080p', 'blu-ray', 'hdrip'], ['bd50', '1080p', '720p', 'brrip']),
        (['dvdrip'], ['dvdrip']),
        (['dvd'], ['dvdr']),
    ]

    def _search(self, media, quality, results):

        data = self.getHTMLData(self.urls['search'] % (self.getDomain(), 'm', getIdentifier(media).replace('tt', '')))

        if data:

            cat_ids = self.getCatId(quality)

            try:
                html = BeautifulSoup(data)
                resultdiv = html.find('div', attrs = {'class': 'tabs'})
                for result in resultdiv.find_all('div', recursive = False):
                    if result.get('id').lower().strip('tab-') not in cat_ids:
                        continue

                    try:
                        for temp in result.find_all('tr'):
                            if temp['class'] is 'firstr' or not temp.get('id'):
                                continue

                            new = {}

                            column = 0
                            for td in temp.find_all('td'):
                                if column == self.COLUMN_NAME:
                                    link = td.find('div', {'class': 'torrentname'}).find_all('a')[2]
                                    new['id'] = temp.get('id')[-7:]
                                    new['name'] = link.text
                                    new['url'] = td.find('a', 'imagnet')['href']
                                    new['detail_url'] = self.urls['detail'] % (self.getDomain(), link['href'][1:])
                                    new['verified'] = True if td.find('a', 'iverify') else False
                                    new['score'] = 100 if new['verified'] else 0
                                elif column == self.COLUMN_SIZE:
                                    new['size'] = self.parseSize(td.text)
                                elif column == self.COLUMN_AGE:
                                    new['age'] = self.ageToDays(td.text)
                                elif column == self.COLUMN_SEEDS:
                                    new['seeders'] = tryInt(td.text)
                                elif column == self.COLUMN_LEECHERS:
                                    new['leechers'] = tryInt(td.text)

                                column += 1

                            # Only store verified torrents
                            if self.conf('only_verified') and not new['verified']:
                                continue

                            results.append(new)
                    except:
                        log.error('Failed parsing KickAssTorrents: %s', traceback.format_exc())

            except AttributeError:
                log.debug('No search results found.')
