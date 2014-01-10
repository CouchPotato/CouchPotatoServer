from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import getTitle, tryInt, mergeDicts
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
from dateutil.parser import parse
import htmlentitydefs
import json
import re
import time
import traceback

log = CPLog(__name__)


class PassThePopcorn(TorrentProvider):

    urls = {
         'domain': 'https://tls.passthepopcorn.me',
         'detail': 'https://tls.passthepopcorn.me/torrents.php?torrentid=%s',
         'torrent': 'https://tls.passthepopcorn.me/torrents.php',
         'login': 'https://tls.passthepopcorn.me/ajax.php?action=login',
         'login_check': 'https://tls.passthepopcorn.me/ajax.php?action=login',
         'search': 'https://tls.passthepopcorn.me/search/%s/0/7/%d'
    }

    http_time_between_calls = 2

    quality_search_params = {
        'bd50':     {'media': 'Blu-ray', 'format': 'BD50'},
        '1080p':    {'resolution': '1080p'},
        '720p':     {'resolution': '720p'},
        'brrip':    {'media': 'Blu-ray'},
        'dvdr':     {'resolution': 'anysd'},
        'dvdrip':   {'media': 'DVD'},
        'scr':      {'media': 'DVD-Screener'},
        'r5':       {'media': 'R5'},
        'tc':       {'media': 'TC'},
        'ts':       {'media': 'TS'},
        'cam':      {'media': 'CAM'}
    }

    post_search_filters = {
        'bd50':     {'Codec': ['BD50']},
        '1080p':    {'Resolution': ['1080p']},
        '720p':     {'Resolution': ['720p']},
        'brrip':    {'Source': ['Blu-ray'], 'Quality': ['High Definition'], 'Container': ['!ISO']},
        'dvdr':     {'Codec': ['DVD5', 'DVD9']},
        'dvdrip':   {'Source': ['DVD'], 'Codec': ['!DVD5', '!DVD9']},
        'scr':      {'Source': ['DVD-Screener']},
        'r5':       {'Source': ['R5']},
        'tc':       {'Source': ['TC']},
        'ts':       {'Source': ['TS']},
        'cam':      {'Source': ['CAM']}
    }

    def _search(self, movie, quality, results):

        movie_title = getTitle(movie['library'])
        quality_id = quality['identifier']

        params = mergeDicts(self.quality_search_params[quality_id].copy(), {
            'order_by': 'relevance',
            'order_way': 'descending',
            'searchstr': movie['library']['identifier']
        })

        url = '%s?json=noredirect&%s' % (self.urls['torrent'], tryUrlencode(params))
        res = self.getJsonData(url)

        try:
            if not 'Movies' in res:
                return

            authkey = res['AuthKey']
            passkey = res['PassKey']

            for ptpmovie in res['Movies']:
                if not 'Torrents' in ptpmovie:
                    log.debug('Movie %s (%s) has NO torrents', (ptpmovie['Title'], ptpmovie['Year']))
                    continue

                log.debug('Movie %s (%s) has %d torrents', (ptpmovie['Title'], ptpmovie['Year'], len(ptpmovie['Torrents'])))
                for torrent in ptpmovie['Torrents']:
                    torrent_id = tryInt(torrent['Id'])
                    torrentdesc = '%s %s %s' % (torrent['Resolution'], torrent['Source'], torrent['Codec'])
                    torrentscore = 0

                    if 'GoldenPopcorn' in torrent and torrent['GoldenPopcorn']:
                        torrentdesc += ' HQ'
                        if self.conf('prefer_golden'):
                            torrentscore += 200
                    if 'Scene' in torrent and torrent['Scene']:
                        torrentdesc += ' Scene'
                        if self.conf('prefer_scene'):
                            torrentscore += 50
                    if 'RemasterTitle' in torrent and torrent['RemasterTitle']:
                        torrentdesc += self.htmlToASCII(' %s' % torrent['RemasterTitle'])

                    torrentdesc += ' (%s)' % quality_id
                    torrent_name = re.sub('[^A-Za-z0-9\-_ \(\).]+', '', '%s (%s) - %s' % (movie_title, ptpmovie['Year'], torrentdesc))

                    def extra_check(item):
                        return self.torrentMeetsQualitySpec(item, quality_id)

                    results.append({
                        'id': torrent_id,
                        'name': torrent_name,
                        'Source': torrent['Source'],
                        'Checked': 'true' if torrent['Checked'] else 'false',
                        'Resolution': torrent['Resolution'],
                        'url': '%s?action=download&id=%d&authkey=%s&torrent_pass=%s' % (self.urls['torrent'], torrent_id, authkey, passkey),
                        'detail_url': self.urls['detail'] % torrent_id,
                        'date': tryInt(time.mktime(parse(torrent['UploadTime']).timetuple())),
                        'size': tryInt(torrent['Size']) / (1024 * 1024),
                        'seeders': tryInt(torrent['Seeders']),
                        'leechers': tryInt(torrent['Leechers']),
                        'score': torrentscore,
                        'extra_check': extra_check,
                    })

        except:
            log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def torrentMeetsQualitySpec(self, torrent, quality):

        if not quality in self.post_search_filters:
            return True

        reqs = self.post_search_filters[quality].copy()

        if self.conf('require_approval'):
            log.debug('Config: Require staff-approval activated')
            reqs['Checked'] = ['true']

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
            text = m.group(0)
            if text[:2] == "&#":
                # character reference
                try:
                    if text[:3] == "&#x":
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except ValueError:
                    pass
            else:
                # named entity
                try:
                    text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text # leave as is
        return re.sub("&#?\w+;", fixup, u'%s' % text)

    def unicodeToASCII(self, text):
        import unicodedata
        return ''.join(c for c in unicodedata.normalize('NFKD', text) if unicodedata.category(c) != 'Mn')

    def htmlToASCII(self, text):
        return self.unicodeToASCII(self.htmlToUnicode(text))

    def getLoginParams(self):
        return {
             'username': self.conf('username'),
             'password': self.conf('password'),
             'passkey': self.conf('passkey'),
             'keeplogged': '1',
             'login': 'Login'
        }

    def loginSuccess(self, output):
        try:
            return json.loads(output).get('Result', '').lower() == 'ok'
        except:
            return False

    loginCheckSuccess = loginSuccess
