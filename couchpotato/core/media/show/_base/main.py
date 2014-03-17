import time

from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, fireEventAsync, addEvent
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media import MediaBase


log = CPLog(__name__)


class ShowBase(MediaBase):

    _type = 'show'
    query_condenser = QueryCondenser()

    def __init__(self):
        super(ShowBase, self).__init__()

        addApiView('show.add', self.addView, docs = {
            'desc': 'Add new show to the wanted list',
            'params': {
                'identifier': {'desc': 'IMDB id of the show your want to add.'},
                'profile_id': {'desc': 'ID of quality profile you want the add the show in. If empty will use the default profile.'},
                'category_id': {'desc': 'ID of category you want the add the show in.'},
                'title': {'desc': 'Title of the show to use for search and renaming'},
            }
        })

        addEvent('show.add', self.add)
        addEvent('show.update_info', self.add)

        addEvent('media.search_query', self.query)

    def query(self, library, first = True, condense = True, **kwargs):
        if library is list or library.get('type') != 'show':
            return

        titles = [title['title'] for title in library['titles']]

        if condense:
            # Use QueryCondenser to build a list of optimal search titles
            condensed_titles = self.query_condenser.distinct(titles)

            if condensed_titles:
                # Use condensed titles if we got a valid result
                titles = condensed_titles
            else:
                # Fallback to simplifying titles
                titles = [simplify(title) for title in titles]

        if first:
            return titles[0] if titles else None

        return titles

    def addView(self, **kwargs):
        add_dict = self.add(params = kwargs)

        return {
            'success': True if add_dict else False,
            'show': add_dict,
        }

    def add(self, params = {}, force_readd = True, search_after = True, update_library = False, status = None):

        db = get_db()

        # Add Show
        show = {
            'identifiers': {
                'imdb': 'tt1234',
                'thetvdb': 123,
                'tmdb': 123,
                'rage': 123
            },
            'status': 'active',
            'title': title,
            'description': description,
            'profile_id': profile_id,
            'category_id': category_id,
            'primary_provider': 'thetvdb',
            'absolute_nr': True,
            'info': {}
        }

        show_info = fireEvent('show.info', show.get('identifiers'))

        # Add Seasons
        for season_info in show_info.get('seasons', []):

            season = fireEvent('show.season.add', show.get('_id'), season_info)

            for episode_info in season_info.get('seasons', []):

                fireEvent('show.episode.add', season.get('_id'), episode_info)
