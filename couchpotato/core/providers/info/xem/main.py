from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.info.base import ShowProvider
from couchpotato.core.helpers.encoding import tryUrlencode
import traceback

log = CPLog(__name__)


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

    # TODO: Also get show aliases (store as titles)
    def getShowInfo(self, identifier = None):
        if self.isDisabled():
            return {}

        cache_key = 'xem.cache.%s' % identifier
        log.debug('Getting showInfo: %s', cache_key)
        result = self.getCache(cache_key) or {}
        if result:
            return result

        # Create season/episode and absolute mappings
        url =  self.config['url_all'] + "id=%s&origin=tvdb" % tryUrlencode(identifier)
        response = self.getJsonData(url)
        if response:
            if response.get('result') == 'success':
                data = response.get('data', None)
                result = self._parse(data)

        # Create name alias mappings
        url =  self.config['url_names'] + "id=%s&origin=tvdb" % tryUrlencode(identifier)
        response = self.getJsonData(url)
        if response:
            if response.get('result') == 'success':
                data = response.get('data', None)
                result.update({'map_names': data})

        self.setCache(cache_key, result)
        return result

    def getEpisodeInfo(self, identifier = None, params = {}):
        episode = params.get('episode', None)
        if episode is None:
            return False

        season_identifier = params.get('season_identifier', None)
        if season_identifier is None:
            return False

        episode_identifier = params.get('episode_identifier', None)
        absolute = params.get('absolute', None)

        # season_identifier must contain the 'show id : season number' since there is no tvdb id
        # for season and we need a reference to both the show id and season number
        if season_identifier:
            try:
                identifier, season_identifier = season_identifier.split(':')
                season = int(season_identifier)
            except: return False

        result = self.getShowInfo(identifier)
        map = {}
        if result:
            map_episode = result.get('map_episode', {}).get(season, {}).get(episode, {})
            if map_episode:
                map.update({'map_episode': map_episode})

            if absolute:
                map_absolute = result.get('map_absolute', {}).get(absolute, {})
                if map_absolute:
                    map.update({'map_absolute': map_absolute})

            map_names = result.get('map_names', {}).get(season, {}).get(episode, {})
            if map_names:
                map.update({'map_names': map_names})

        return map


    def _parse(self, data, master = 'tvdb'):
        '''parses xem map and returns a custom formatted dict map

        To retreive map for scene:
        if 'scene' in map['map_episode'][1][1]:
            print map['map_episode'][1][1]['scene']['season']
        '''
        if not isinstance(data, list):
            return {}

        map = {'map_episode': {}, 'map_absolute': {}}
        for maps in data:
            origin = maps.pop(master, None)
            if origin is None:
                continue # No master origin to map to
            map.get('map_episode').setdefault(origin['season'], {}).setdefault(origin['episode'], maps.copy())
            map.get('map_absolute').setdefault(origin['absolute'], maps.copy())

        return map

    def isDisabled(self):
        if __name__ == '__main__':
            return False
        if self.conf('enabled'):
            return False
        else:
            return True

#XXX: REMOVE, just for degugging
def main():
    """Simple example of using xem
    """
    xem_instance = Xem()
    print xem_instance.getShowInfo(identifier=73141) # (American Dad)

if __name__ == '__main__':
    main()