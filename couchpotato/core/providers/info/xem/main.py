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
            "79604": ["Black-Lagoon", "ブラック・ラグーン", "Burakku Ragūn"],
            "248812": ["Dont Trust the Bitch in Apartment 23", "Don't Trust the Bitch in Apartment 23"],
            "257571": ["Nazo no Kanojo X"],
            "257875": ["Lupin III - Mine Fujiko to Iu Onna", "Lupin III Fujiko to Iu Onna", "Lupin the Third - Mine Fujiko to Iu Onna"]
            },
    "message": ""
    }
    '''

    def __init__(self):
        addEvent('show.search', self.search, priority = 5)
        addEvent('show.info', self.getShowInfo, priority = 5)
        addEvent('season.info', self.getSeasonInfo, priority = 5)
        addEvent('episode.info', self.getEpisodeInfo, priority = 5)

        self.config = {}
        self.config['base_url']   = "http://thexem.de"
        self.config['url_single'] = u"%(base_url)s/map/single?" % self.config
        self.config['url_all']    = u"%(base_url)s/map/all?" % self.config
        self.config['url_names']  = u"%(base_url)s/map/allNames?" % self.config

    def search(self, q, limit = 12, language='en'):
        pass

    def getShow(self, identifier = None):
        pass

    def getShowInfo(self, identifier = None):
        if self.isDisabled():
            return False
        url =  self.config['url_all'] + "id=%s&origin=tvdb" % tryUrlencode(identifier)
        response = self.getJsonData(url)
        if response:
            if response.get('result') == 'success':
                map = response.get('data', None)
                if map:
                    return dict(map = map)
        return False

    def getSeasonInfo(self, identifier=None, season_identifier=None):
        pass

    def getEpisodeInfo(self, identifier=None, season_identifier=None, episode_identifier=None):
        pass

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