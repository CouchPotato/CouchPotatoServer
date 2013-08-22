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

    def debug(self,  identifier):
        """
        XXX: This is only a hook for a breakpoint so we can test database stuff easily
        REMOVE when finished
        """
        from couchpotato import get_session
        from couchpotato.core.event import addEvent, fireEventAsync, fireEvent
        from couchpotato.core.helpers.encoding import toUnicode, simplifyString
        from couchpotato.core.logger import CPLog
        from couchpotato.core.plugins.base import Plugin
        from couchpotato.core.settings.model import Library, LibraryTitle, File
        from string import ascii_letters
        import time
        import traceback

        db = get_session()
        parent = db.query(Library).filter_by(identifier = identifier).first()
        return

    def add(self, params = {}, force_readd = True, search_after = True, update_library = False, status_id = None):
        """
        1. Add Show
        2. Add All Episodes
        3. Add All Seasons

        Notes, not to forget:
        - relate parent and children, possible grandparent to grandchild so episodes know it belong to show, etc
        - looks like we dont send info to library; it comes later
        - change references to plot to description
        - change Model to Media

        params
        {'category_id': u'-1',
         'identifier': u'tt1519931',
         'profile_id': u'12',
         'thetvdb_id': u'158661',
         'title': u'Haven'}
        """
        log.debug("show.add")

        # Add show parent to db first
        parent =  self.addToDatabase(params = params,  type = 'show')

        identifier = params.get('id')

        # XXX: add seasons
        # XXX: Fix so we dont have a nested list [0] (fireEvent)
        try:
            seasons = fireEvent('season.info', identifier = identifier)[0]
        except: return None
        if seasons is not None:
            for season in seasons:
                season['title'] = season.get('title',  None)
                season_id =  season.get('id', None)
                if season_id is None: continue
                season['identifier'] = season_id
                season['parent_identifier'] = identifier
                self.addToDatabase(params=season, type = "season")

                # XXX: Fix so we dont have a nested list [0] (fireEvent)
                try:
                    episodes = fireEvent('episode.info', identifier = identifier, season_identifier = season_id)[0]
                except: continue
                if episodes is not None:
                    for episode in episodes:
                        episode['title'] = episode.get('titles', None)[0] # XXX. [0] will create exception. FIX!
                        episode_id =  episode.get('id', None)
                        if episode_id is None: continue
                        episode['identifier'] = episode_id
                        episode['parent_identifier'] = season['identifier']
                        self.addToDatabase(params=episode, type = "episode")

        self.debug(str(identifier)) # XXX: Remove TODO:  Add Show(extend Library) convience options for db seasching
        return parent

    def addToDatabase(self, params = {}, type="show", force_readd = True, search_after = True, update_library = False, status_id = None):
        log.debug("show.addToDatabase")

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

        library = fireEvent('library.add.%s' % type, single = True, attrs = params, update_after = update_library)
        if not library:
            return False

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
                type = type,
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

            fireEventAsync('library.update.%s' % type, params.get('identifier'), default_title = params.get('title', ''), on_complete = onComplete)
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
            log.debug('Show already exists, not updating: %s', params)
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

    def createOnComplete(self, show_id):

        def onComplete():
            db = get_session()
            show = db.query(Movie).filter_by(id = show_id).first()
            fireEventAsync('show.searcher.single', show.to_dict(self.default_dict), on_complete = self.createNotifyFront(show_id))
            db.expire_all()

        return onComplete

    def createNotifyFront(self, show_id):

        def notifyFront():
            db = get_session()
            show = db.query(Movie).filter_by(id = show_id).first()
            fireEvent('notify.frontend', type = 'show.update.%s' % show.id, data = show.to_dict(self.default_dict))
            db.expire_all()

        return notifyFront
