#from couchpotato.core.logger import CPLog
#from couchpotato.core.media import MediaBase

#log = CPLog(__name__)


#class ShowBase(MediaBase):

    #identifier = 'show'

    #def __init__(self):
        #super(ShowBase, self).__init__()

from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync, addEvent
from couchpotato.core.helpers.encoding import toUnicode, simplifyString
from couchpotato.core.helpers.variable import getImdb, splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media import MediaBase
from couchpotato.core.settings.model import Library, LibraryTitle, Movie, \
    Release
from couchpotato.environment import Env
from sqlalchemy.orm import joinedload_all
from sqlalchemy.sql.expression import or_, asc, not_, desc
from string import ascii_lowercase
import time

log = CPLog(__name__)


class ShowBase(MediaBase):

    identifier = 'show'

    default_dict = {
        'profile': {'types': {'quality': {}}},
        'releases': {'status': {}, 'quality': {}, 'files':{}, 'info': {}},
        'library': {'titles': {}, 'files':{}},
        'files': {},
        'status': {}
    }

    def __init__(self):
        super(ShowBase, self).__init__()

        addApiView('show.search', self.search, docs = {
            'desc': 'Search the show providers for a show',
            'params': {
                'q': {'desc': 'The (partial) show name you want to search for'},
            },
            'return': {'type': 'object', 'example': """{
    'success': True,
    'empty': bool, any shows returned or not,
    'shows': array, shows found,
}"""}
        })

    def search(self, q = '', **kwargs):

        cache_key = u'%s/%s' % (__name__, simplifyString(q))
        shows = Env.get('cache').get(cache_key)

        if not shows:

            if getImdb(q):
                shows = [fireEvent('show.info', identifier = q, merge = True)]
            else:
                shows = fireEvent('show.search', q = q, merge = True)
            Env.get('cache').set(cache_key, shows)

        return {
            'success': True,
            'empty': len(shows) == 0 if shows else 0,
            'shows': shows,
        }

