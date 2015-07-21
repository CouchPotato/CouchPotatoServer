from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)

class Base(TorrentProvider):

    urls = {
        'search': 'https://getstrike.net/api/v2/torrents/search/?phrase=%s&category=%s',
        'test': 'https://getstrike.net/torrents/'
    }

    cat_backup_id = 200
    disable_provider = False
    http_time_between_calls = 1

    def _searchOnTitle(self, title, movie, quality, results):
        url = self.urls['search'] % (title,self.getCategoryName())
        json = self.getJsonData(url)
        items = self.processJson(json)
        for item in items:
            results.append(item)

    def extra_score(self, item):
        extraScore = int(self.conf('extra_score'))
        return extraScore

    def processJson(self, json):
        resultItems = []
        for item in json[u'torrents']:
            resultItems.append({
                'id': item['torrent_hash'],
                'imdbid': item['imdbid'],
                'name': item['torrent_title'],
                'url': item['magnet_uri'],
                'detail_url': item['page'],
                'size': item['size']/(1024*1024),
                'seeders': item['seeds'],
                'leechers': item['leeches']#,
                #'extra_score': self.extra_score
                #'get_more_info': self.getMoreInfo
            })
        return resultItems

config = [{
    'name': 'strikeapi',
    'groups': [
        {
            'tab': 'searcher',
                    'list': 'torrent_providers',
                    'name': 'StrikeApi',
                    'description': 'Media made easy',
                    'wizard': True,
                    'icon': 'R0lGODlhEAAQAPcAACp2gDN7hTl/iD2Ciz6DjD+EjECFjUOGj0WHkEaIkUiJkkmKkkuLk06NlVaSmleTm1iUm1yWnmKaoWaco2edpGiepWygp3Kkq3qqsH6ssoOvtYSwtoizuIqzuYu1uoy1uo+3vJG4vZa7wJe8wZi9wZ/BxaLDx6bFyafGyqnHy7DM0LTO0rfR1LjR1LnR1bnS1b7V2MTZ28XZ3Mba3Mrd38zf4NLh49Xk5dbk5tzo6t7q6+Dr7OHr7ebv8Orx8ury8+3z9O/09fD19vH29vP4+Pf5+fj6+/v8/f39/f///wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwAAAAAEAAQAAAIpACT1PiwI4nBgwgPLjCRgMOQhBANIDFC4sCJIxAPGphBIIgPDA1kZEwi0UEPgzciVNAREYmDEgEOGHSh4EXCkiJAFEjhAISRIjdd5iygoYOECwM82GBJUqhODSIOEHhBAQADgzhBCKiwQoUKFgs2CMHq9EMGHTgiTMiBUCIEBCGS/AAZo6WPHEBGHECBsSWSFQ2JjEyCAMYDCzwGG2xxgYZigwEBADs=',
                    'options': [
                        {
                            'name': 'enabled',
                            'type': 'enabler',
                            'default': False
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
                }
            ]
        }]