from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider

log = CPLog(__name__)


class ThePirateBay(TorrentProvider):

    urls = {
        'download': 'http://torrents.depiraatbaai.be/%s/%s.torrent',
        'nfo': 'https://depiraatbaai.be/torrent/%s',
        'detail': 'https://depiraatbaai.be/torrent/%s',
        'search': 'https://depiraatbaai.be/search/%s/0/7/%d',
    }

    cat_ids = [
        ([207], ['720p', '1080p']),
        ([200], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr', 'brrip']),
        ([202], ['dvdr'])
    ]
    cat_backup_id = 200

    ignore_string = {
        '720p': ' -brrip -bdrip',
        '1080p': ' -brrip -bdrip'
    }

    def __init__(self):
        pass

    def find(self, movie, quality, type):

        results = []
        if not self.enabled():
            return results

        url = self.apiUrl % (quote_plus(self.toSearchString(movie.name + ' ' + quality) + self.makeIgnoreString(type)), self.getCatId(type))

        log.info('Searching: %s', url)

        data = self.urlopen(url)
        if not data:
            log.error('Failed to get data from %s.', url)
            return results

        try:
            tables = SoupStrainer('table')
            html = BeautifulSoup(data, parseOnlyThese = tables)
            resultTable = html.find('table', attrs = {'id':'searchResult'})
            for result in resultTable.findAll('tr'):
                details = result.find('a', attrs = {'class':'detLink'})
                if details:
                    href = re.search('/(?P<id>\d+)/', details['href'])
                    id = href.group('id')
                    name = self.toSaveString(details.contents[0])
                    desc = result.find('font', attrs = {'class':'detDesc'}).contents[0].split(',')
                    date = ''
                    size = 0
                    for item in desc:
                        # Weird date stuff
                        if 'uploaded' in item.lower():
                            date = item.replace('Uploaded', '')
                            date = date.replace('Today', '')

                            # Do something with yesterday
                            yesterdayMinus = 0
                            if 'Y-day' in date:
                                date = date.replace('Y-day', '')
                                yesterdayMinus = 86400

                            datestring = date.replace('&nbsp;', ' ').strip()
                            date = int(time.mktime(parse(datestring).timetuple())) - yesterdayMinus
                        # size
                        elif 'size' in item.lower():
                            size = item.replace('Size', '')

                    seedleech = []
                    for td in result.findAll('td'):
                        try:
                            seedleech.append(int(td.contents[0]))
                        except ValueError:
                            pass

                    seeders = 0
                    leechers = 0
                    if len(seedleech) == 2 and seedleech[0] > 0 and seedleech[1] > 0:
                        seeders = seedleech[0]
                        leechers = seedleech[1]

                    # to item
                    new = self.feedItem()
                    new.id = id
                    new.type = 'torrent'
                    new.name = name
                    new.date = date
                    new.size = self.parseSize(size)
                    new.seeders = seeders
                    new.leechers = leechers
                    new.url = self.downloadLink(id, name)
                    new.score = self.calcScore(new, movie) + self.uploader(result) + (seeders / 10)

                    if seeders > 0 and (new.date + (int(self.conf('wait')) * 60 * 60) < time.time()) and Qualities.types.get(type).get('minSize') <= new.size:
                        new.detailUrl = self.detailLink(id)
                        new.content = self.getInfo(new.detailUrl)
                        if self.isCorrectMovie(new, movie, type):
                            results.append(new)
                            log.info('Found: %s', new.name)

            return results

        except AttributeError:
            log.debug('No search results found.')

        return []

    def makeIgnoreString(self, type):
        ignore = self.ignoreString.get(type)
        return ignore if ignore else ''

    def uploader(self, html):
        score = 0
        if html.find('img', attr = {'alt':'VIP'}):
            score += 3
        if html.find('img', attr = {'alt':'Trusted'}):
            score += 1
        return score


    def getInfo(self, url):
        log.debug('Getting info: %s', url)

        data = self.urlopen(url)
        if not data:
            log.error('Failed to get data from %s.', url)
            return ''

        div = SoupStrainer('div')
        html = BeautifulSoup(data, parseOnlyThese = div)
        html = html.find('div', attrs = {'class':'nfo'})
        return str(html).decode("utf-8", "replace")

    def downloadLink(self, id, name):
        return self.downloadUrl % (id, quote_plus(name))

    def isEnabled(self):
        return self.conf('enabled') and TorrentProvider.isEnabled(self)
