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
        addApiView('show.add', self.addView, docs = {
            'desc': 'Add new movie to the wanted list',
            'params': {
                'identifier': {'desc': 'IMDB id of the movie your want to add.'},
                'profile_id': {'desc': 'ID of quality profile you want the add the movie in. If empty will use the default profile.'},
                'title': {'desc': 'Movie title to use for searches. Has to be one of the titles returned by movie.search.'},
            }
        })
        
        addEvent('show.add', self.add)

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

    def addView(self, **kwargs):

        movie_dict = fireEvent('show.add', params=kwargs)  # XXX: Temp added so we can catch a breakpoint
        #movie_dict = self.add(params = kwargs)

        return {
            'success': True,
            'added': True if movie_dict else False,
            'movie': movie_dict,
        }
    
    def add(self, params = {}, force_readd = True, search_after = True, update_library = False, status_id = None):
        """
        1. Add Show
        1. Add All Episodes
        2. Add All Seasons
        
        Notes, not to forget:
        - relate parent and children, possible grandparent to grandchild so episodes know it belong to show, etc
        - looks like we dont send info to library; it comes later
        - change references to plot to description
        - change Model to Media
        """
        log.debug("show.add")
        
        
        identifier = params.get('thetvdb_id')
        episodes = fireEvent('show.episodes', identifier = identifier)
        
        # XXX: Fix so we dont have a nested list
        for episode in episodes[0]:
            self.add2(params=episode)

        return self.add2(params = params)

    def add2(self, params = {}, force_readd = True, search_after = True, update_library = False, status_id = None):
        log.debug("show.add2")
        
        if not params.get('identifier'):
            msg = 'Can\'t add show without imdb identifier.'
            log.error(msg)
            fireEvent('notify.frontend', type = 'show.is_tvshow', message = msg)
            return False
        #else:
            #try:
                #is_show = fireEvent('movie.is_show', identifier = params.get('identifier'), single = True)
                #if not is_show:
                    #msg = 'Can\'t add show, seems to be a TV show.'
                    #log.error(msg)
                    #fireEvent('notify.frontend', type = 'show.is_tvshow', message = msg)
                    #return False
            #except:
                #pass


        library = fireEvent('library.add', single = True, attrs = params, update_after = update_library)

        # Status
        status_active, snatched_status, ignored_status, done_status, downloaded_status = \
            fireEvent('status.get', ['active', 'snatched', 'ignored', 'done', 'downloaded'], single = True)

        default_profile = fireEvent('profile.default', single = True)
        cat_id = params.get('category_id', None)

        db = get_session()
        m = db.query(Movie).filter_by(library_id = library.get('id')).first()
        added = True
        do_search = False
        if not m:
            m = Movie(
                library_id = library.get('id'),
                profile_id = params.get('profile_id', default_profile.get('id')),
                status_id = status_id if status_id else status_active.get('id'),
                category_id = tryInt(cat_id) if cat_id is not None and tryInt(cat_id) > 0 else None,
            )
            db.add(m)
            db.commit()

            onComplete = None
            if search_after:
                onComplete = self.createOnComplete(m.id)

            fireEventAsync('library.update', params.get('identifier'), default_title = params.get('title', ''), on_complete = onComplete)
            search_after = False
        elif force_readd:

            # Clean snatched history
            for release in m.releases:
                if release.status_id in [downloaded_status.get('id'), snatched_status.get('id'), done_status.get('id')]:
                    if params.get('ignore_previous', False):
                        release.status_id = ignored_status.get('id')
                    else:
                        fireEvent('release.delete', release.id, single = True)

            m.profile_id = params.get('profile_id', default_profile.get('id'))
            m.category_id = tryInt(cat_id) if cat_id is not None and tryInt(cat_id) > 0 else None
        else:
            log.debug('Movie already exists, not updating: %s', params)
            added = False

        if force_readd:
            m.status_id = status_id if status_id else status_active.get('id')
            m.last_edit = int(time.time())
            do_search = True

        db.commit()

        # Remove releases
        available_status = fireEvent('status.get', 'available', single = True)
        for rel in m.releases:
            if rel.status_id is available_status.get('id'):
                db.delete(rel)
                db.commit()

        show_dict = m.to_dict(self.default_dict)

        if do_search and search_after:
            onComplete = self.createOnComplete(m.id)
            onComplete()

        if added:
            fireEvent('notify.frontend', type = 'show.added', data = show_dict, message = 'Successfully added "%s" to your wanted list.' % params.get('title', ''))

        db.expire_all()
        return show_dict

    def createOnComplete(self, movie_id):

        def onComplete():
            db = get_session()
            movie = db.query(Movie).filter_by(id = movie_id).first()
            fireEventAsync('movie.searcher.single', movie.to_dict(self.default_dict), on_complete = self.createNotifyFront(movie_id))
            db.expire_all()

        return onComplete
    
    def createNotifyFront(self, movie_id):

        def notifyFront():
            db = get_session()
            movie = db.query(Movie).filter_by(id = movie_id).first()
            fireEvent('notify.frontend', type = 'show.update.%s' % movie.id, data = movie.to_dict(self.default_dict))
            db.expire_all()

        return notifyFront
