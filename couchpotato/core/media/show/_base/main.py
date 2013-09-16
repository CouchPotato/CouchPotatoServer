from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync, addEvent
from couchpotato.core.helpers.encoding import toUnicode, simplifyString
from couchpotato.core.helpers.variable import getImdb, splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media import MediaBase
from couchpotato.core.settings.model import Library, LibraryTitle, Media, \
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
        params
        {'category_id': u'-1',
         'identifier': u'tt1519931',
         'profile_id': u'12',
         'thetvdb_id': u'158661',
         'title': u'Haven'}
        """
        log.debug("show.add")

        # Add show parent to db first; need to update library so maps will be in place (if any)
        parent = self.addToDatabase(params = params, update_library = True, type = 'show')

        # TODO: add by airdate

        # Add by Season/Episode numbers
        self.addBySeasonEpisode(parent,
                                params = params,
                                force_readd = force_readd,
                                search_after = search_after,
                                update_library = update_library,
                                status_id = status_id
                                )

    def addBySeasonEpisode(self, parent, params = {}, force_readd = True, search_after = True, update_library = False, status_id = None):
        identifier = params.get('id')
        # 'tvdb' will always be the master for our purpose.  All mapped data can be mapped
        # to another source for downloading, but it will always be remapped back to tvdb numbering
        # when renamed so media can be used in media players that use tvdb for info provider
        #
        # This currently means the episode must actually exist in tvdb in order to be found but
        # the numbering can be different

        #master = 'tvdb'
        #destination = 'scene'
        #destination = 'anidb'
        #destination = 'rage'
        #destination = 'trakt'
        # TODO: auto mode.  if anime exists use it. if scene exists use it else use tvdb

        # XXX: We should abort adding show, etc if either tvdb or xem is down or we will have incorrent mappings
        #      I think if tvdb gets error we wont have anydata anyway, but we must make sure XEM returns!!!!

        # Only the master should return results here; all other info providers should just return False
        # since we are just interested in the structure at this point.
        seasons = fireEvent('season.info', merge = True, identifier = identifier)
        if seasons is not None:
            for season in seasons:
                # Make sure we are only dealing with 'tvdb' responses at this point
                if season.get('primary_provider', None) != 'thetvdb':
                    continue
                season_id =  season.get('id', None)
                if season_id is None: continue

                season_params = {'season_identifier':  season_id}
                # Calling all info providers; merge your info now for individual season
                single_season = fireEvent('season.info', merge = True, identifier = identifier, params = season_params)
                single_season['title'] = single_season.get('original_title',  None)
                single_season['identifier'] = season_id
                single_season['parent_identifier'] = identifier
                log.info("Adding Season %s" % season_id)
                s = self.addToDatabase(params = single_season, type = "season")

                episode_params = {'season_identifier':  season_id}
                episodes = fireEvent('episode.info', merge = True, identifier = identifier, params = episode_params)
                if episodes is not None:
                    for episode in episodes:
                        # Make sure we are only dealing with 'tvdb' responses at this point
                        if episode.get('primary_provider', None) != 'thetvdb':
                            continue
                        episode_id =  episode.get('id', None)
                        if episode_id is None: continue
                        try:
                            episode_number = int(episode.get('episodenumber', None))
                        except (ValueError, TypeError):
                            continue
                        try:
                            absolute_number = int(episode.get('absolute_number', None))
                        except (ValueError, TypeError):
                            absolute_number = None

                        episode_params = {'season_identifier':  season_id,
                                          'episode_identifier': episode_id,
                                          'episode':            episode_number}
                        if absolute_number:
                            episode_params['absolute'] = absolute_number
                        # Calling all info providers; merge your info now for individual episode
                        single_episode = fireEvent('episode.info', merge = True, identifier = identifier, params = episode_params)
                        single_episode['title'] = single_episode.get('original_title', None)
                        single_episode['identifier'] = episode_id
                        single_episode['parent_identifier'] = single_season['identifier']
                        log.info("Adding [%sx%s] %s - %s" % (season_id,
                                                             episode_number,
                                                             params['title'],
                                                             single_episode.get('original_title',  '')))
                        e = self.addToDatabase(params = single_episode, type = "episode")

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
        m = db.query(Media).filter_by(library_id = library.get('id')).first()
        added = True
        do_search = False
        if not m:
            m = Media(
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
            show = db.query(Media).filter_by(id = show_id).first()
            fireEventAsync('show.searcher.single', show.to_dict(self.default_dict), on_complete = self.createNotifyFront(show_id))
            db.expire_all()

        return onComplete

    def createNotifyFront(self, show_id):

        def notifyFront():
            db = get_session()
            show = db.query(Media).filter_by(id = show_id).first()
            fireEvent('notify.frontend', type = 'show.update.%s' % show.id, data = show.to_dict(self.default_dict))
            db.expire_all()

        return notifyFront
