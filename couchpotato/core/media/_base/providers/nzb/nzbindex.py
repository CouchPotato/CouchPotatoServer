import re
import time

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.nzb.base import NZBProvider
from dateutil.parser import parse


log = CPLog(__name__)


class Base(NZBProvider, RSS):

    urls = {
        'download': 'https://www.nzbindex.com/download/',
        'search': 'https://www.nzbindex.com/rss/?%s',
    }

    http_time_between_calls = 1  # Seconds

    def _search(self, media, quality, results):

        nzbs = self.getRSSData(self.urls['search'] % self.buildUrl(media, quality))

        for nzb in nzbs:

            enclosure = self.getElement(nzb, 'enclosure').attrib
            nzbindex_id = int(self.getTextElement(nzb, "link").split('/')[4])

            title = self.getTextElement(nzb, "title")

            match = fireEvent('matcher.parse', title, parser='usenet', single = True)
            if not match.chains:
                log.info('Unable to parse release with title "%s"', title)
                continue

            # TODO should we consider other lower-weight chains here?
            info = fireEvent('matcher.flatten_info', match.chains[0].info, single = True)

            release_name = fireEvent('matcher.construct_from_raw', info.get('release_name'), single = True)

            file_name = info.get('detail', {}).get('file_name')
            file_name = file_name[0] if file_name else None

            title = release_name or file_name

            # Strip extension from parsed title (if one exists)
            ext_pos = title.rfind('.')

            # Assume extension if smaller than 4 characters
            # TODO this should probably be done a better way
            if len(title[ext_pos + 1:]) <= 4:
                title = title[:ext_pos]

            if not title:
                log.info('Unable to find release name from match')
                continue

            try:
                description = self.getTextElement(nzb, "description")
            except:
                description = ''

            def extra_check(item):
                if '#c20000' in item['description'].lower():
                    log.info('Wrong: Seems to be passworded: %s', item['name'])
                    return False

                return True

            results.append({
                'id': nzbindex_id,
                'name': title,
                'age': self.calculateAge(int(time.mktime(parse(self.getTextElement(nzb, "pubDate")).timetuple()))),
                'size': tryInt(enclosure['length']) / 1024 / 1024,
                'url': enclosure['url'],
                'detail_url': enclosure['url'].replace('/download/', '/release/'),
                'description': description,
                'get_more_info': self.getMoreInfo,
                'extra_check': extra_check,
            })

    def getMoreInfo(self, item):
        try:
            if '/nfo/' in item['description'].lower():
                nfo_url = re.search('href=\"(?P<nfo>.+)\" ', item['description']).group('nfo')
                full_description = self.getCache('nzbindex.%s' % item['id'], url = nfo_url, cache_timeout = 25920000)
                html = BeautifulSoup(full_description)
                item['description'] = toUnicode(html.find('pre', attrs = {'id': 'nfo0'}).text)
        except:
            pass


config = [{
    'name': 'nzbindex',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'nzb_providers',
            'name': 'nzbindex',
            'description': 'Free provider, less accurate. See <a href="https://www.nzbindex.com/">NZBIndex</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True,
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
