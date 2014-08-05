import re
import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://awesome-hd.net/',
        'detail': 'https://awesome-hd.net/torrents.php?torrentid=%s',
        'search': 'https://awesome-hd.net/searchapi.php?action=imdbsearch&passkey=%s&imdb=%s&internal=%s',
        'download': 'https://awesome-hd.net/torrents.php?action=download&id=%s&authkey=%s&torrent_pass=%s',
    }
    http_time_between_calls = 1

    def _search(self, movie, quality, results):

        data = self.getHTMLData(self.urls['search'] % (self.conf('passkey'), getIdentifier(movie), self.conf('only_internal')))

        if data:
            try:
                soup = BeautifulSoup(data)

                if soup.find('error'):
                    log.error(soup.find('error').get_text())
                    return

                authkey = soup.find('authkey').get_text()
                entries = soup.find_all('torrent')

                for entry in entries:

                    torrentscore = 0
                    torrent_id = entry.find('id').get_text()
                    name = entry.find('name').get_text()
                    year = entry.find('year').get_text()
                    releasegroup = entry.find('releasegroup').get_text()
                    resolution = entry.find('resolution').get_text()
                    encoding = entry.find('encoding').get_text()
                    freeleech = entry.find('freeleech').get_text()
                    torrent_desc = '/ %s / %s / %s ' % (releasegroup, resolution, encoding)

                    if freeleech == '0.25' and self.conf('prefer_internal'):
                        torrent_desc += '/ Internal'
                        torrentscore += 200

                    if encoding == 'x264' and self.conf('favor') in ['encode', 'both']:
                        torrentscore += 300
                    if re.search('Remux', encoding) and self.conf('favor') in ['remux', 'both']:
                        torrentscore += 200

                    results.append({
                        'id': torrent_id,
                        'name': re.sub('[^A-Za-z0-9\-_ \(\).]+', '', '%s (%s) %s' % (name, year, torrent_desc)),
                        'url': self.urls['download'] % (torrent_id, authkey, self.conf('passkey')),
                        'detail_url': self.urls['detail'] % torrent_id,
                        'size': tryInt(entry.find('size').get_text()) / 1048576,
                        'seeders': tryInt(entry.find('seeders').get_text()),
                        'leechers': tryInt(entry.find('leechers').get_text()),
                        'score': torrentscore
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))


config = [{
    'name': 'awesomehd',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'Awesome-HD',
            'description': '<a href="https://awesome-hd.net">AHD</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAC+UlEQVR4AV1SO0y6dxQ9H4g8CoIoohZ5NA0aR2UgkYpNB5uocTSaLlrDblMH09Gt8d90r3YpJkanxjA4GGkbO7RNxSABq8jDGnkpD+UD5NV7Bxvbk9wvv+/3uPece66A/yEWi42FQqHVfD7/cbPZtIEglUpjOp3uZHR0dBvAn3gDIRqNgjE4OKj0+Xzf3NzcfD4wMCCjf5TLZbTbbajVatzf3+Pu7q5uNpt35ufnvwBQAScQRREEldfr9RWLxan+/n5YrVa+jFarhVfQQyQSCU4EhULhX15engEgSrjC0dHRVqlUmjQYDBgaGgKtuTqz4mTgIoVCASaTCX19fajVapOHh4dbFJBks9mxcDi8qtFoJEajkfVyJWi1WkxMTMDhcIAT8x6D7/Dd6+vr1fHx8TGp2+3+iqo5+YCzBwIBToK5ubl/mQwPDyMSibAs2Gw2UHNRrValz8/PDUk8Hv9EqVRCr9fj4uICTNflcqFer+Pg4AB7e3uoVCq8x9Rxfn6O7u5uqFQq8FspZXxHTekggByA3W4Hr9PpNDeRL3I1cMhkMrBrnZ2dyGQyvNYIs7OzVbJNPjIyAraLwYdcjR8wXl5eIJfLwRIFQQDLYkm3t7c1CdGPPT4+cpOImp4PODMeaK+n10As2jBbrHifHOjS6qAguVFimkqlwAMmIQnHV1dX4NDQhVwuhyZTV6pgIktzDzkkk0lEwhEEzs7ASQr5Ai4vL1nuccfCwsLO/v6+p9FoyJhF6ekJro/cPCzIZLNQa7rQoK77/SdgWWpKkCaJ5EB9aWnpe6nH40nRMBnJV4f5gw+FX3/5GX/8/htXRZdOzzqhJWn6nl6YbTZqqhrhULD16fT0d8FgcFtYW1vD5uamfGVl5cd4IjldKhZACdkJvKfWUANrxEaJV4hiGVaL1b+7653hXzwRZQr2X76xsfG1xWIRaZzbNPv/CdrjEL9cX/+WXFBSgEPgzxuwG3Yans9OT0+naBZMIJDNfzudzp8WFxd/APAX3uAf9WOTxOPLdosAAAAASUVORK5CYII=',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'passkey',
                    'default': '',
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
                    'name': 'only_internal',
                    'advanced': True,
                    'type': 'bool',
                    'default': 1,
                    'description': 'Only search for internal releases.'
                },
                {
                    'name': 'prefer_internal',
                    'advanced': True,
                    'type': 'bool',
                    'default': 1,
                    'description': 'Favors internal releases over non-internal releases.'
                },
                {
                    'name': 'favor',
                    'advanced': True,
                    'default': 'both',
                    'type': 'dropdown',
                    'values': [('Encodes & Remuxes', 'both'), ('Encodes', 'encode'), ('Remuxes', 'remux'), ('None', 'none')],
                    'description': 'Give extra scoring to encodes or remuxes.'
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'type': 'int',
                    'default': 20,
                    'description': 'Starting score for each release found via this provider.',
                },
            ],
        },
    ],
}]

