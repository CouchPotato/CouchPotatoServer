import time

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.nzb.base import NZBProvider
from dateutil.parser import parse


log = CPLog(__name__)


class Base(NZBProvider, RSS):

    urls = {
        'search': 'https://www.nzbclub.com/nzbrss.aspx?%s',
    }

    http_time_between_calls = 4  # seconds

    def _search(self, media, quality, results):

        nzbs = self.getRSSData(self.urls['search'] % self.buildUrl(media))

        for nzb in nzbs:

            nzbclub_id = tryInt(self.getTextElement(nzb, "link").split('/nzb_view/')[1].split('/')[0])
            enclosure = self.getElement(nzb, "enclosure").attrib
            size = enclosure['length']
            date = self.getTextElement(nzb, "pubDate")

            def extra_check(item):
                full_description = self.getCache('nzbclub.%s' % nzbclub_id, item['detail_url'], cache_timeout = 25920000)

                for ignored in ['ARCHIVE inside ARCHIVE', 'Incomplete', 'repair impossible']:
                    if ignored in full_description:
                        log.info('Wrong: Seems to be passworded or corrupted files: %s', item['name'])
                        return False

                return True

            results.append({
                'id': nzbclub_id,
                'name': toUnicode(self.getTextElement(nzb, "title")),
                'age': self.calculateAge(int(time.mktime(parse(date).timetuple()))),
                'size': tryInt(size) / 1024 / 1024,
                'url': enclosure['url'].replace(' ', '_'),
                'detail_url': self.getTextElement(nzb, "link"),
                'get_more_info': self.getMoreInfo,
                'extra_check': extra_check
            })

    def getMoreInfo(self, item):
        full_description = self.getCache('nzbclub.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('pre', attrs = {'class': 'nfo'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

    def extraCheck(self, item):
        full_description = self.getCache('nzbclub.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)

        if 'ARCHIVE inside ARCHIVE' in full_description:
            log.info('Wrong: Seems to be passworded files: %s', item['name'])
            return False

        return True


config = [{
    'name': 'nzbclub',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'nzb_providers',
            'name': 'NZBClub',
            'description': 'Free provider, less accurate. See <a href="https://www.nzbclub.com/" target="_blank">NZBClub</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAACEUlEQVQ4y3VSMWgUQRR9/8/s7OzeJSdnTsVGghLEYBNQjBpQiRBFhIB2EcHG1kbs0murhZAmVocExEZQ0c7CxkLINYcJJpoYj9wZcnu72fF21uJSXMzuhyne58/j/fcf4b+KokgBIOSU53lxP5b9oNVqDT36dH+5UjoiKvIwPFEEgWBshGZ3E7/NOupL9fMjx0e+ZhKsrq+c/FPZKJi0w4FsQXMBDEJsd7BNW9h2tuyP9vfTALIJkMIu1hYRtINM+dpzcWc0sbkreK4fUEogyraAmKGF3+7vcT/wtR9QwkCabSAzQQuvk0uglAo5YaQ5DASGYjfMXcHVOqKu6NmR7iehlKAdHWUqWPv1c3i+9uwVdRlEBGaGEAJCCrDo9ShhvF6qPq8tL57bp+DbRn2sHtUuCY9YphLMu5921VhrwYJ5tbt0tt6sjQP4vEfB2Ikz7/ytwbeR6ljHkXCUA6UcOLtPOg4MYhtH8ZcLw5er+xQMDAwEURRNl96X596Y6oxFwsw9fmtTOAr2Ik19nL365FZpsLSdnQPPM8aYewc+lDcX4rkHqbQMAGTJXulOLzycmr1bKBTi3DOGYagajcahiaOT89fbM0/dxEsUu3aidfPljWO3HzebzYNBELi5Z5RSJlrrHd/3w8lT114MrVTWOn875fHRiYVisRhorWMpZXdvNnLKGCOstb0AMlulVJI19w/+nceU4D0aCwAAAABJRU5ErkJggg==',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]
