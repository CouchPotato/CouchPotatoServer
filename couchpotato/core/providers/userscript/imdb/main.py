from beautifulsoup import BeautifulSoup
from couchpotato.core.providers.userscript.base import UserscriptBase
import re


class IMDB(UserscriptBase):

    includes = ['http*://*.imdb.com/title/tt*', 'http*://imdb.com/title/tt*']

    def getMovie(self, url):

        data = self.urlopen(url)

        html = BeautifulSoup(data)
        headers = html.findAll('h5')

        # Don't add TV show
        for head in headers:
            if 'seasons' in head.lower():
                return False

        return {
            'id': re.search('(?P<id>tt[0-9{7}]+)', url).group('id'),
            'year': self.getYear(html)
        }

    def getYear(self, html):

        headers = html.findAll('h1')

        tv_pattern = '/^\((TV|Video) ([0-9]+)\)$/';

        try:
            year = headers[0].findAll('a').text
            return year
        except:
            pass

        for head in headers:
            match = re.search(tv_pattern, head)
            if match:
                return match[1]

#CouchPotato['imdb.com'] = (function(){
#
#    function isMovie(){
#        var series = document.getElementsByTagName('h5')
#        for (var i = 0; i < series.length; i++) {
#            if (series[i].innerHTML == 'Seasons:') {
#                return false;
#            }
#        }
#        return true;
#    }
#
#    function getId(){
#        return 'tt' + location.href.replace(/[^\d+]+/g, '');
#    }
#
#    function getYear(){
#        try {
#            return document.getElementsByTagName('h1')[0].getElementsByTagName('a')[0].text;
#        } catch (e) {
#            var spans = document.getElementsByTagName('h1')[0].getElementsByTagName('span');
#            var pattern = /^\((TV|Video) ([0-9]+)\)$/;
#            for (var i = 0; i < spans.length; i++) {
#                if (spans[i].innerHTML.search(pattern)) {
#                    return spans[i].innerHTML.match(pattern)[1];
#                }
#            }
#        }
#    }
#
#    var constructor = function(){
#        if(isMovie()){
#            lib.osd(getId(), getYear());
#        }
#    }
#
#    return constructor;
#
#})();
