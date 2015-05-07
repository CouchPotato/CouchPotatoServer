import re
import traceback

from couchpotato.core.helpers.variable import tryInt, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://hdaccess.net/',
        'detail': 'https://hdaccess.net/details.php?id=%s',
        'search': 'https://hdaccess.net/searchapi.php?apikey=%s&username=%s&imdbid=%s&internal=%s',
        'download': 'https://hdaccess.net/grab.php?torrent=%s&apikey=%s',
    }

    http_time_between_calls = 1  # Seconds

    def _search(self, movie, quality, results):
        data = self.getJsonData(self.urls['search'] % (self.conf('apikey'), self.conf('username'), getIdentifier(movie), self.conf('internal_only')))

        if data:
            try:
                #for result in data[]:
                for key, result in data.iteritems():
                    if tryInt(result['total_results']) == 0:
                        return
                    torrentscore = self.conf('extra_score')
                    releasegroup = result['releasegroup']
                    resolution = result['resolution']
                    encoding = result['encoding']
                    freeleech = tryInt(result['freeleech'])
                    seeders = tryInt(result['seeders'])
                    torrent_desc = '/ %s / %s / %s / %s seeders' % (releasegroup, resolution, encoding, seeders)

                    if freeleech > 0 and self.conf('prefer_internal'):
                        torrent_desc += '/ Internal'
                        torrentscore += 200

                    if seeders == 0:
                        torrentscore = 0

                    name = result['release_name']
                    year = tryInt(result['year'])

                    results.append({
                        'id': tryInt(result['torrentid']),
                        'name': re.sub('[^A-Za-z0-9\-_ \(\).]+', '', '%s (%s) %s' % (name, year, torrent_desc)),
                        'url': self.urls['download'] % (result['torrentid'], self.conf('apikey')),
                        'detail_url': self.urls['detail'] % result['torrentid'],
                        'size': tryInt(result['size']),
                        'seeders': tryInt(result['seeders']),
                        'leechers': tryInt(result['leechers']),
                        'age': tryInt(result['age']),
                        'score': torrentscore
                    })
            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))
config = [{
    'name': 'hdaccess',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'HDAccess',
            'wizard': True,
            'description': '<a href="https://hdaccess.net">HDAccess</a>',
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAADuUlEQVQ4yz3T209bdQAH8O/vnNNzWno5FIpAKZdSLi23gWMDtumWuSXOyzJj9M1kyIOPS1xiYuKe9GUPezZZnGIiMTqTxS1bdIuYkG2MWKBAKYVszOgKFkrbA+259HfO+fli/PwPHzI+Pg5CCEAI2VcUlEsl1tHdU7P5bGOkWChEaaUCwvHpmkD93POn6bwgCMQGAMYYYwyCruuQnE7SPzjIstvb8l+bm5fXkokJSmlQEkUQAIpSRH5vd0tyum7I/sA1Z5VH2ctmiGWZjHw4McE1NAZtQ9fD25kXt1VN7es7dNjuGRjiJFeVpWo6slsZPhF/Ys/PPeIs2056ff7zIOS5rpU5/viJEwwEnu3Mi18dojjw0aWP6amz57h9RSE/35zinq2nuGjvIQwOj7K2SKeZWkk0auXSSZ+/ZopSy+CbW1pQKpWu6Jr2/qVPPqWRjm6HWi6Tm999g3RyGbndLCqGgVBrO3F7fHykK0YX47NNtGLYlBq/c+H2iD+3k704dHQUDcFmQVXLyP6zhfTqCl45fQYjx17FemoJunoAk1bQFGoVhkdPwNC0ix2dMT+3llodM02rKdo7gN3dHAEhuH/vNgDg3Pl3cPaNt2GZJpYX5lBbFwClBukfGobL5WrayW6NccVCISY4HIQxYts2Q3J5CXOPHuLlo6NoCoXQ2hbG0JFRpJYWcVDIQ5ZlyL5qW5b9hNlWjKsYBgzDgKppMCoGHty7A0orOHbyNNweL+obGnDm9TdhWSYS8Vn4a2shOZ0QJRGSKIHjeGGtWNhjqqpyG+k04k8eozPai9ZwByavf4kfpyZxZGwMfYOHsbwQx34hB5dL4syKweRq/xpXHwzNapqWSSYWMDszzYqFPEaOn4KiKJiZfoCZ6d8Am+GtC++iXCpjaf4P9vefT8HzfKarp3eWRKMxCILwuWXSz977YIK2RTodDoGH1+OG1+tDlbsKkuiAJEngeWBjNUUnv7rucIiOLyzTvMKJTgnVtbVXLctK3L31g+NAUajL5bEptaDpOnTdgGkzVHl9drms0ju3fnJIkphoaQtfbQiFwAcCAY5wnCE5Xff3i8XX4o9nGksH+8zl9hAGZlWMCivkc9z0L3fZ999+LTCGZKi55YJTFHfye3sc6e/vB88LpK6+iWlqSS4WcpcNXZtwOp3B6mo/REmCSSkEgd+qq3vpRkt75Fp9Y1BZWZwnhq4zEovF/u/MATAti4U7umvyu9kR27aikihC9vvTnV2xufVUMu/2uIksy/9tZvgX49fLmAMx3bsAAAAASUVORK5CYII=',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'username',
                    'default': '',
                    'description': 'Enter your site username.',
                },
                {
                    'name': 'apikey',
                    'default': '',
                    'label': 'API Key',
                    'description': 'Enter your site api key. This can be find on <a href="https://hdaccess.net/usercp.php?action=security">Profile Security</a>',
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 0,
                    'description': 'Will not be (re)moved until this seed ratio is met. HDAccess minimum is 1:1.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 0,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met. HDAccess minimum is 48 hours.',
                },
                {
                    'name': 'prefer_internal',
                    'advanced': True,
                    'type': 'bool',
                    'default': 1,
                    'description': 'Favors internal releases over non-internal releases.',
                },
                {
                    'name': 'internal_only',
                    'advanced': True,
                    'label': 'Internal Only',
                    'type': 'bool',
                    'default': False,
                    'description': 'Only download releases marked as HDAccess internal',
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
