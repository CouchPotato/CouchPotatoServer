from couchpotato.core.helpers.rss import RSS
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class Kinepolis(Automation, RSS):

    urls = {
        'top10': 'http://kinepolis.be/nl/top10-box-office/feed',
    }


    def getIMDBids(self):

        if self.isDisabled():
            return

        movies = []
        for key in self.urls:
            url = self.urls[key]
            cache_key = 'kinepolis.%s' % key

            rss_data = self.getCache(cache_key, url)
            try:
                items = self.getElements(XMLTree.fromstring(rss_data), 'channel/item')
            except Exception, e:
                log.debug('%s, %s' % (self.getName(), e))
                continue

            for item in items:
                title = self.getTextElement(item, "title").lower()
                result = self.search(title)

                if result:
                    if not self.conf('automation_use_requirements') or self.isMinimal(result):
                        movies.append(result)

        return movies
