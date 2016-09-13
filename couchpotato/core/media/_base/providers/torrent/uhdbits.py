import htmlentitydefs
import json
import re
import time
import traceback

from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import getTitle, tryInt, mergeDicts, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from dateutil.parser import parse
import six


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'login': 'https://uhdbits.org/login.php',
        'login_check': 'https://uhdbits.org/inbox.php',
        'api': 'https://uhdbits.org/ajax.php',
        'detail': 'https://uhdbits.org/torrents.php'
    }

    login_errors = 0
    http_time_between_calls = 2

    def _search(self, media, quality, results):

        movie_title = getTitle(media)
        media_year = media['info']['year']
        quality_id = quality['identifier']
        
        params = mergeDicts(self.quality_search_params[quality_id].copy(), {
            'searchstr': getTitle(media),
            'year': media['info']['year']
        })

        url = '%s?action=browse&%s' % (self.urls['api'], tryUrlencode(params))
        res = self.getJsonData(url)
        
        try:
            if not 'response' in res:
                return

            auth_url = '%s?action=index' % (self.urls['api'])
            auth_res = self.getJsonData(auth_url)
        
            authkey = auth_res['response']['authkey']
            passkey = auth_res['response']['passkey']
            
            for uhdmovie in res['response']['results']:
                if not 'torrents' in uhdmovie:
                    log.debug('Movie %s (%s) has NO torrents', (uhdmovie['groupName'], uhdmovie['groupYear']))
                    continue
                    
                moviegroup_id = tryInt(uhdmovie['groupId'])

                log.debug('Movie %s (%s) has %d torrents', (uhdmovie['groupName'], uhdmovie['groupYear'], len(uhdmovie['torrents'])))
                for torrent in uhdmovie['torrents']:
                    torrent_id = tryInt(torrent['torrentId'])
                    torrentdesc = '%s %s' % (torrent['format'], torrent['media'])
                    torrentscore = 0

                    if 'isFreeleech' in torrent and torrent['isFreeleech']:
                        torrentdesc += ' Freeleech'
                        if self.conf('prefer_freeleech'):
                           torrentscore += 7000
                    if 'scene' in torrent and torrent['scene']:
                        torrentdesc += ' Scene'
                        if self.conf('prefer_scene'):
                            torrentscore += 2000
                    if 'remastered' in torrent and torrent['remasterTitle']:
                        torrentdesc += self.htmlToASCII(' %s' % torrent['remasterTitle'])

                    torrentdesc += ' (%s)' % quality_id
                    torrent_name = re.sub('[^A-Za-z0-9\-_ \(\).]+', '', '%s (%s) - %s' % (movie_title, uhdmovie['groupYear'], torrentdesc))

                    def extra_check(item):
                        return self.torrentMeetsQualitySpec(item, quality_id)

                    results.append({
                        'id': torrent_id,
                        'name': torrent_name,
                        'Source': torrent['media'],
                        'Resolution': torrent['format'],
                        'url': '%s?action=download&id=%d&authkey=%s&torrent_pass=%s' % (self.urls['detail'], torrent_id, authkey, passkey),
                        'detail_url': '%s?id=%s&torrentid=%s' % (self.urls['detail'], moviegroup_id, torrent_id),
                        'date': tryInt(time.mktime(parse(torrent['time']).timetuple())),
                        'size': tryInt(torrent['size']) / (1024 * 1024),
                        'seeders': tryInt(torrent['seeders']),
                        'leechers': tryInt(torrent['leechers']),
                        'score': torrentscore,
                        'extra_check': extra_check,
                    })
                    
        except:
            log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def torrentMeetsQualitySpec(self, torrent, quality):

        if not quality in self.post_search_filters:
            return True

        reqs = self.post_search_filters[quality].copy()

        for field, specs in reqs.items():
            matches_one = False
            seen_one = False

            if not field in torrent:
                log.debug('Torrent with ID %s has no field "%s"; cannot apply post-search-filter for quality "%s"', (torrent['id'], field, quality))
                continue

            for spec in specs:
                if len(spec) > 0 and spec[0] == '!':
                    # a negative rule; if the field matches, return False
                    if torrent[field] == spec[1:]:
                        return False
                else:
                    # a positive rule; if any of the possible positive values match the field, return True
                    log.debug('Checking if torrents field %s equals %s' % (field, spec))
                    seen_one = True
                    if torrent[field] == spec:
                        log.debug('Torrent satisfied %s == %s' % (field, spec))
                        matches_one = True

            if seen_one and not matches_one:
                log.debug('Torrent did not satisfy requirements, ignoring')
                return False

        return True

    def htmlToUnicode(self, text):
        def fixup(m):
            txt = m.group(0)
            if txt[:2] == "&#":
                # character reference
                try:
                    if txt[:3] == "&#x":
                        return unichr(int(txt[3:-1], 16))
                    else:
                        return unichr(int(txt[2:-1]))
                except ValueError:
                    pass
            else:
                # named entity
                try:
                    txt = unichr(htmlentitydefs.name2codepoint[txt[1:-1]])
                except KeyError:
                    pass
            return txt  # leave as is
        return re.sub("&#?\w+;", fixup, six.u('%s') % text)

    def unicodeToASCII(self, text):
        import unicodedata
        return ''.join(c for c in unicodedata.normalize('NFKD', text) if unicodedata.category(c) != 'Mn')

    def htmlToASCII(self, text):
        return self.unicodeToASCII(self.htmlToUnicode(text))

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'keeplogged': '1'
        }

    def loginSuccess(self, output):
        try:
            if 'logout.php' in output.lower():
                self.login_errors = 0
                return True
        except:
            pass

        self.login_errors += 1
        if self.login_errors >= 3:
            log.error('Disabling UHDBits provider after repeated failed logins. '
                      'Please check your configuration. Re-enabling without '
                      'solving the problem may cause an IP ban. response=%s',
                      output)
            self.conf('enabled', value=False)
            self.login_errors = 0

        return False

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'uhdbits',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'UHDBits',
            'description': '<a href="https://uhdbits.org">UHDBits</a>',
            'wizard': True,
            'icon': 'R0lGODlhEAAQAPAAAOgADAAAACH5BAEAAAEALAAAAAAQABAAAAImBBJ2qWuoYDuPudrk3Vvrbn1eaHFZ+Z0qxrbjCsJvRNITHN0mUgAAOw==',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
                {
                    'name': 'prefer_freeleech',
                    'advanced': True,
                    'type': 'bool',
                    'label': 'Prefer Freeleech',
                    'default': 1,
                    'description': 'Favors torrents marked as freeleech over all other releases.'
                },
                {
                    'name': 'prefer_scene',
                    'advanced': True,
                    'type': 'bool',
                    'label': 'Prefer scene',
                    'default': 0,
                    'description': 'Favors scene-releases over non-scene releases.'
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 2,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 96,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 20,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        }
    ]
}]
