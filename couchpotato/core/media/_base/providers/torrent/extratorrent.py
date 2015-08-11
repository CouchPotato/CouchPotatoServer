import math
import re
import traceback

from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import tryInt, tryFloat
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)

class Base(TorrentProvider):

    field_link = 0
    field_name = 2
    field_size = 3
    field_seeders = 4
    field_leechers = 5

    max_pages = 2

    category = 0 # any category

    urls = {
        'url': '%s%s',
        'detail': '%s%s',
        'search': '%s/advanced_search/?page=%d&with=%s&s_cat=%d&seeds_from=1'
    }

    http_time_between_calls = 1  # Seconds

    proxy_list = [
        'http://extratorrent.cc'
    ]

    def buildUrl(self, *args, **kwargs):
        media = kwargs.get('media', None)
        title = kwargs.get('title', None)
        page = kwargs.get('page', 1)
        if not title and media:
            title = fireEvent('library.query', media, single = True)
        if not title:
            return False
        assert isinstance(page, (int, long))

        return self.urls['search'] % (self.getDomain(), page, tryUrlencode(title), self.category)

    def _searchOnTitle(self, title, media, quality, results):
        page = 1
        pages = self.max_pages
        while page <= pages:
            url = self.buildUrl(title=title, media=media, page=page)
            data = self.getHTMLData(url)
            try:
                html = BeautifulSoup(data)
                if page == 1:
                    matches = re.search('total .b.([0-9]+)..b. torrents found', data, re.MULTILINE)
                    torrents_total = tryFloat(matches.group(1))
                    option = html.find('select', attrs={'name': 'torr_cat'}).find('option', attrs={'selected': 'selected'})
                    torrents_per_page = tryFloat(option.text)
                    pages = math.ceil(torrents_total / torrents_per_page)
                    if self.max_pages < pages:
                        pages = self.max_pages

                for tr in html.find_all('tr', attrs={'class': ['tlr', 'tlz']}):
                    result = { }
                    field = self.field_link
                    for td in tr.find_all('td'):
                        if field == self.field_link:
                            a = td.find('a', title=re.compile('^download ', re.IGNORECASE))
                            result['url'] = self.urls['url'] % (self.getDomain(), a.get('href'))
                        elif field == self.field_name:
                            a = None
                            for a in td.find_all('a', title=re.compile('^view ', re.IGNORECASE)): pass
                            if a:
                                result['id'] = re.search('/torrent/(?P<id>\d+)/', a.get('href')).group('id')
                                result['name'] = a.text
                                result['detail_url'] = self.urls['detail'] % (self.getDomain(), a.get('href'))
                        elif field == self.field_size:
                            result['size'] = self.parseSize(td.text)
                        elif field == self.field_seeders:
                            result['seeders'] = tryInt(td.text)
                        elif field == self.field_leechers:
                            result['leechers'] = tryInt(td.text)

                        field += 1
                    # /for

                    if all(key in result for key in ('url', 'id', 'name', 'detail_url', 'size', 'seeders', 'leechers')):
                        results.append(result)
                # /for
            except:
                log.error('Failed parsing results from ExtraTorrent: %s', traceback.format_exc())
                break

            page += 1
        # /while

config = [{
    'name': 'extratorrent',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'ExtraTorrent',
            'description': '<a href="http://extratorrent.cc/">ExtraTorrent</a>',
            'wizard': True,
            'icon': 'AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAQAQAAAAAAAAAAAAAAAAAAAAAAADIvb7/xry9/8e8vf/Ivb7/yL2+/8i9vv/Ivb7/yL2+/8i9vv/Ivb7/yL2+/8i9vv/Ivb7/x7y9/8a8vf/Ivb7/xry9//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7//v7+//7+/v/+/v7/xry9/8e8vf/8/Pz//Pz8/5OTkv9qSRj/akkY/2tKGf9rShn/a0oZ/2tKGP9qSRj/Tzoc/4iEff/8/Pz//Pz8/8e8vf/HvL3/+/v7//v7+/+Hf3P/4bd0/+G3dP/ht3T/4bd0/+G3dP/ht3T/4bd0/3hgOv9xbmr/+/v7//v7+//HvL3/x7y9//f4+P/3+Pj/hHxx/+zAfP/swHz/7MB8/3xzaP9yal3/cmpd/3JqXf98c2b/xcPB//f4+P/3+Pj/x7y9/8e8vf/29vb/9vb2/4V9cf/txYX/7cWF/2RSNv/Nz8//zs/R/87P0P/Mzs7/29va//f39//29vb/9vb2/8e8vf/HvL3/8/Pz//Pz8/+IgHP/78yU/+/MlP94YDr/8vLy//Ly8v/y8vL/8vLy//Ly8v/09PT/8/T0//Lz8//HvL3/x7y9//Ly8v/y8vL/h4F5/+/Pnf/vz53/kHdP/3hgOv94YDr/eWE7/3hgOv9USDf/5eLd//Ly8v/y8vL/x7y9/8e8vf/w8PD/8PDw/4eBef/t0Kf/7dCn/+3Qp//t0Kf/7dCn/+3Qp//t0Kf/VEg3/9vb2v/w7+//8PDw/8e8vf/HvL3/7u3u/+7t7v+Gg33/7dm8/+3ZvP/Txa7/cW5r/3Fua/9xbmv/d3Rv/62rqf/o5+f/7u3u/+7t7v/HvL3/x7y9/+vr6//r6+v/h4F4/+/l0P/v5dD/XFVM/8XHx//Fx8f/xcfH/8TGxv/r7Ov/6+vr/+vr6//r6+v/x7y9/8e8vf/p6un/6erp/4eAeP/58+b/+fPm/4iEff93dG7/fXl0/356df99eXT/bGlj/5OTkf/p6un/6erp/8e8vf/HvL3/6Ofn/+fn5/+GgHj/5uPd/+bj3f/m493/5uPd/+bj3f/m493/5uPd/3Z2df9vb2//6Ofn/+fn5//HvL3/x7y9/+fn5//n5+f/raqo/3Z2df94eHj/d3d2/3h4ef95eXn/eHh4/3h4eP94eHj/ramo/+fn5//n5+f/x7y9/8a8vf/l5eX/5eXl/+Xl5f/l5eX/5eXl/+Xl5f/l5eX/5eXl/+Xl5f/l5eX/5eXl/+Xl5f/l5eX/5eXl/8a8vf/Ivb7/xry9/8e8vf/Ivb7/yL2+/8i9vv/Ivb7/yL2+/8i9vv/Ivb7/yL2+/8i9vv/Ivb7/x7y9/8a8vf/Ivb7/AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//w==',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 1,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 40,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
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
