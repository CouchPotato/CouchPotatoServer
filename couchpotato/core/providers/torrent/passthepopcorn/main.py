from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import getTitle, tryInt, mergeDicts
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
from dateutil.parser import parse
import cookielib
import htmlentitydefs
import json
import re
import time
import traceback
import urllib2

log = CPLog(__name__)


class PassThePopcorn(TorrentProvider):

    urls = {
         'domain': 'https://tls.passthepopcorn.me',
         'detail': 'https://tls.passthepopcorn.me/torrents.php?torrentid=%s',
         'torrent': 'https://tls.passthepopcorn.me/torrents.php',
         'login': 'https://tls.passthepopcorn.me/ajax.php?action=login',
         'search': 'https://tls.passthepopcorn.me/search/%s/0/7/%d'
    }

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

    class NotLoggedInHTTPError(urllib2.HTTPError):
        def __init__(self, url, code, msg, headers, fp):
            urllib2.HTTPError.__init__(self, url, code, msg, headers, fp)

    class PTPHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            log.debug("302 detected; redirected to %s", headers['Location'])
            if (headers['Location'] != 'login.php'):
                return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
            else:
                raise PassThePopcorn.NotLoggedInHTTPError(req.get_full_url(), code, msg, headers, fp)

    def _search(self, movie, quality, results):

        movie_title = getTitle(movie['library'])
        quality_id = quality['identifier']

        params = mergeDicts(self.quality_search_params[quality_id].copy(), {
            'order_by': 'relevance',
            'order_way': 'descending',
            'searchstr': movie['library']['identifier']
        })

        # Do login for the cookies
        if not self.login_opener and not self.login():
            return

        try:
            url = '%s?json=noredirect&%s' % (self.urls['torrent'], tryUrlencode(params))
            txt = self.urlopen(url, opener = self.login_opener)
            res = json.loads(txt)
        except:
            log.error('Search on PassThePopcorn.me (%s) failed (could not decode JSON)', params)
            return

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
                        'download': self.loginDownload,
                    })

        except:
            log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def login(self):

        cookieprocessor = urllib2.HTTPCookieProcessor(cookielib.CookieJar())
        opener = urllib2.build_opener(cookieprocessor, PassThePopcorn.PTPHTTPRedirectHandler())
        opener.addheaders = [
            ('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.75 Safari/537.1'),
            ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
            ('Accept-Language', 'en-gb,en;q=0.5'),
            ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
            ('Keep-Alive', '115'),
            ('Connection', 'keep-alive'),
            ('Cache-Control', 'max-age=0'),
        ]

        try:
            response = opener.open(self.urls['login'], self.getLoginParams())
        except urllib2.URLError as e:
            log.error('Login to PassThePopcorn failed: %s', e)
            return False

        if response.getcode() == 200:
            log.debug('Login HTTP status 200; seems successful')
            self.login_opener = opener
            return True
        else:
            log.error('Login to PassThePopcorn failed: returned code %d', response.getcode())
            return False

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
        return tryUrlencode({
             'username': self.conf('username'),
             'password': self.conf('password'),
             'passkey': self.conf('passkey'),
             'keeplogged': '1',
             'login': 'Login'
        })
