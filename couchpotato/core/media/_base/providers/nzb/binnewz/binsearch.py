import urllib
from bs4 import BeautifulSoup
from couchpotato.core.logger import CPLog
import re
from nzbdownloader import NZBDownloader
from nzbdownloader import NZBPostURLSearchResult
from couchpotato.core.helpers.variable import tryInt, tryFloat
log = CPLog(__name__)

class BinSearch(NZBDownloader):

    def search(self, filename, minSize, newsgroup=None):
        filename=filename.encode('utf8')
        if newsgroup != None:
            binSearchURLs = [  urllib.urlencode({'server' : 1, 'max': '250', 'adv_g' : newsgroup, 'q' : filename}), urllib.urlencode({'server' : 2, 'max': '250', 'adv_g' : newsgroup, 'q' : filename})]
        else:
            binSearchURLs = [  urllib.urlencode({'server' : 1, 'max': '250', 'q' : filename}), urllib.urlencode({'server' : 2, 'max': '250', 'q' : filename})]

        for suffixURL in binSearchURLs:
            binSearchURL = "http://binsearch.info/?adv_age=&" + suffixURL
                    
            binSearchSoup = BeautifulSoup( self.open(binSearchURL) )

            foundName = None
            sizeInMegs = None
            main_table = binSearchSoup.find('table', attrs = {'id': 'r2'})
            if not main_table:
                    return

            items = main_table.find_all('tr')
            for row in items:
                    title = row.find('span', attrs = {'class': 's'})

                    if not title: continue

                    nzb_id = row.find('input', attrs = {'type': 'checkbox'})['name']
                    info = row.find('span', attrs = {'class':'d'})
                    try:
                        size_match = re.search('size:.(?P<size>[0-9\.]+.[GMB]+)', info.text)
                    except:
                        continue
                    age = 0
                    try: age = re.search('(?P<size>\d+d)', row.find_all('td')[-1:][0].text).group('size')[:-1]
                    except: pass

                    parts = re.search('available:.(?P<parts>\d+)./.(?P<total>\d+)', info.text)
                    total = float(tryInt(parts.group('total')))
                    parts = float(tryInt(parts.group('parts')))

                    if (total / parts) < 1 and ((total / parts) < 0.95 or ((total / parts) >= 0.95 and not ('par2' in info.text.lower() or 'pa3' in info.text.lower()))):
                        log.info2('Wrong: \'%s\', not complete: %s out of %s', (title, parts, total))
                        continue

                    if 'requires password' in info.text.lower():
                        log.info2('Wrong: \'%s\', passworded', (title))
                        continue
                    sizeInMegs=self.parseSize(size_match.group('size'))
                    if sizeInMegs < minSize:
                        continue
                    postData = title
                    nzbURL = 'https://www.binsearch.info/fcgi/nzb.fcgi?q=' + nzb_id
                    nzbid=nzb_id
                    age=tryInt(age)
                    return NZBPostURLSearchResult( self, nzbURL, postData, sizeInMegs, binSearchURL, age, nzbid )
                
    def parseSize(self, size):
        size_gb = ['gb', 'gib','go']
        size_mb = ['mb', 'mib','mo']
        size_kb = ['kb', 'kib','ko']
        size_raw = size.lower()
        size = tryFloat(re.sub(r'[^0-9.]', '', size).strip())

        for s in size_gb:
            if s in size_raw:
                return size * 1024

        for s in size_mb:
            if s in size_raw:
                return size

        for s in size_kb:
            if s in size_raw:
                return size / 1024

        return 0


