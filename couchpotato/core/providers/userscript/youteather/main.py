from couchpotato.core.providers.userscript.base import UserscriptBase
import re

class YouTheater(UserscriptBase):
    id_re = re.compile("view\.php\?id=(\d+)")
    includes = ['http://www.youtheater.com/view.php?id=*', 'http://youtheater.com/view.php?id=*',
                'http://www.sratim.co.il/view.php?id=*', 'http://sratim.co.il/view.php?id=*']

    def getMovie(self, url):
        id = self.id_re.findall(url)[0]
        url = 'http://www.youtheater.com/view.php?id=%s' % id
        return super(YouTheater, self).getMovie(url)
