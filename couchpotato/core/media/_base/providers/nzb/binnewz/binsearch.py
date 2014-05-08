import urllib
from bs4 import BeautifulSoup
import re
from nzbdownloader import NZBDownloader
from nzbdownloader import NZBPostURLSearchResult
from couchpotato.core.helpers.variable import tryInt

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
            for elem in binSearchSoup.findAll(lambda tag: tag.name=='tr' and 'size:' in tag.text):
                if foundName:
                    break
                for checkbox in elem.findAll(lambda tag: tag.name=='input' and tag.get('type') == 'checkbox'):
                    sizeStr = re.search("size:\s+([^B]*)B", elem.text).group(1).strip()
                    try:
                        age = tryInt(re.search('(?P<size>\d+d)', elem.find_all('td')[-1:][0].text).group('size')[:-1])
                    except:
                        age = 0
                    nzbid = elem.find('input', attrs = {'type':'checkbox'})['name']
                    if "G" in sizeStr:
                        sizeInMegs = float( re.search("([0-9\\.]+)", sizeStr).group(1) ) * 1024
                    elif "K" in sizeStr:
                        sizeInMegs = 0
                    else:
                        sizeInMegs = float( re.search("([0-9\\.]+)", sizeStr).group(1) )
                    
                    if sizeInMegs > minSize:
                        foundName = checkbox.get('name')
                        break
                
            if foundName:
                postData = foundName
                nzbURL = "https://binsearch.info/?adv_age=&" + suffixURL
                return NZBPostURLSearchResult( self, nzbURL, postData, sizeInMegs, binSearchURL, age, nzbid )

