from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.media.show.providers.base import ShowProvider

log = CPLog(__name__)

autoload = 'Xem'


class Xem(ShowProvider):
    '''
    Mapping Information
    ===================

    Single
    ------
    You will need the id / identifier of the show e.g. tvdb-id for American Dad! is 73141
    the origin is the name of the site/entity the episode, season (and/or absolute) numbers are based on

    http://thexem.de/map/single?id=&origin=&episode=&season=&absolute=

    episode, season and absolute are all optional but it wont work if you don't provide either episode and season OR absolute in
    addition you can provide destination as the name of the wished destination, if not provided it will output all available

    When a destination has two or more addresses another entry will be added as _ ... for now the second address gets the index "2"
    (the first index is omitted) and so on

    http://thexem.de/map/single?id=7529&origin=anidb&season=1&episode=2&destination=trakt
    {
     "result":"success",
     "data":{
            "trakt":  {"season":1,"episode":3,"absolute":3},
            "trakt_2":{"season":1,"episode":4,"absolute":4}
            },
     "message":"single mapping for 7529 on anidb."
    }

    All
    ---
    Basically same as "single" just a little easier
    The origin address is added into the output too!!

    http://thexem.de/map/all?id=7529&origin=anidb

    All Names
    ---------
    Get all names xem has to offer
    non optional params: origin(an entity string like 'tvdb')
    optional params: season, language
    - season: a season number or a list like: 1,3,5 or a compare operator like ne,gt,ge,lt,le,eq and a season number. default would
      return all
    - language: a language string like 'us' or 'jp' default is all
    - defaultNames: 1(yes) or 0(no) should the default names be added to the list ? default is 0(no)

    http://thexem.de/map/allNames?origin=tvdb&season=le1

    {
    "result": "success",
    "data": {
            "248812": ["Dont Trust the Bitch in Apartment 23", "Don't Trust the Bitch in Apartment 23"],
            "257571": ["Nazo no Kanojo X"],
            "257875": ["Lupin III - Mine Fujiko to Iu Onna", "Lupin III Fujiko to Iu Onna", "Lupin the Third - Mine Fujiko to Iu Onna"]
            },
    "message": ""
    }
    '''

    def __init__(self):
        addEvent('show.info', self.getShowInfo, priority = 5)
        addEvent('episode.info', self.getEpisodeInfo, priority = 5)

        self.config = {}
        self.config['base_url']   = "http://thexem.de"
        self.config['url_single'] = u"%(base_url)s/map/single?" % self.config
        self.config['url_all']    = u"%(base_url)s/map/all?" % self.config
        self.config['url_names']  = u"%(base_url)s/map/names?" % self.config
        self.config['url_all_names']  = u"%(base_url)s/map/allNames?" % self.config

    def getShowInfo(self, identifiers = None):
        if self.isDisabled():
            return {}

        identifier = identifiers.get('thetvdb')

        if not identifier:
            return {}

        cache_key = 'xem.cache.%s' % identifier
        log.debug('Getting showInfo: %s', cache_key)
        result = self.getCache(cache_key) or {}
        if result:
            return result

        result['seasons'] = {}

        # Create season/episode and absolute mappings
        url = self.config['url_all'] + "id=%s&origin=tvdb" % tryUrlencode(identifier)
        response = self.getJsonData(url)

        if response and response.get('result') == 'success':
            data = response.get('data', None)
            self.parseMaps(result, data)

        # Create name alias mappings
        url = self.config['url_names'] + "id=%s&origin=tvdb" % tryUrlencode(identifier)
        response = self.getJsonData(url)

        if response and response.get('result') == 'success':
            data = response.get('data', None)
            self.parseNames(result, data)

        self.setCache(cache_key, result)
        return result

    def getEpisodeInfo(self, identifiers = None, params = {}):
        episode_num = params.get('episode_number', None)
        if episode_num is None:
            return False

        season_num = params.get('season_number', None)
        if season_num is None:
            return False

        result = self.getShowInfo(identifiers)

        if not result:
            return False

        # Find season
        if season_num not in result['seasons']:
            return False

        season = result['seasons'][season_num]

        # Find episode
        if episode_num not in season['episodes']:
            return False

        return season['episodes'][episode_num]

    def parseMaps(self, result, data, master = 'tvdb'):
        '''parses xem map and returns a custom formatted dict map

        To retreive map for scene:
        if 'scene' in map['map_episode'][1][1]:
            print map['map_episode'][1][1]['scene']['season']
        '''
        if not isinstance(data, list):
            return

        for episode_map in data:
            origin = episode_map.pop(master, None)
            if origin is None:
                continue  # No master origin to map to

            o_season = origin['season']
            o_episode = origin['episode']

            # Create season info
            if o_season not in result['seasons']:
                result['seasons'][o_season] = {}

            season = result['seasons'][o_season]

            if 'episodes' not in season:
                season['episodes'] = {}

            # Create episode info
            if o_episode not in season['episodes']:
                season['episodes'][o_episode] = {}

            episode = season['episodes'][o_episode]
            episode['episode_map'] = episode_map

    def parseNames(self, result, data):
        result['title_map'] = data.pop('all', None)

        for season, title_map in data.items():
            season = int(season)

            # Create season info
            if season not in result['seasons']:
                result['seasons'][season] = {}

            season = result['seasons'][season]
            season['title_map'] = title_map

    def isDisabled(self):
        if __name__ == '__main__':
            return False
        if self.conf('enabled'):
            return False
        else:
            return True


config = [{
    'name': 'xem',
    'groups': [
        {
            'tab': 'providers',
            'name': 'xem',
            'label': 'TheXem',
            'hidden': True,
            'description': 'Used for all calls to TheXem.',
            'options': [
                {
                    'name': 'enabled',
                    'default': True,
                    'label': 'Enabled',
                },
            ],
        },
    ],
}]
