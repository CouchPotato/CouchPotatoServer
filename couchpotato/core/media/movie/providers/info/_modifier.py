import copy
import traceback

from CodernityDB.database import RecordNotFound
from couchpotato import get_db
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import mergeDicts, randomString
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin


log = CPLog(__name__)

autoload = 'MovieResultModifier'


class MovieResultModifier(Plugin):

    default_info = {
        'tmdb_id': 0,
        'titles': [],
        'original_title': '',
        'year': 0,
        'images': {
            'poster': [],
            'backdrop': [],
            'poster_original': [],
            'backdrop_original': [],
            'actors': {},
            'landscape': [],
            'logo': [],
            'clear_art': [],
            'disc_art': [],
            'banner': [],
            'extra_thumbs': [],
            'extra_fanart': []
        },
        'runtime': 0,
        'plot': '',
        'tagline': '',
        'imdb': '',
        'genres': [],
        'mpaa': None,
        'actors': [],
        'actor_roles': {}
    }

    def __init__(self):
        addEvent('result.modify.info.search', self.returnByType)
        addEvent('result.modify.movie.search', self.combineOnIMDB)
        addEvent('result.modify.movie.info', self.checkLibrary)

    def returnByType(self, results):

        new_results = {}
        for r in results:
            type_name = r.get('type', 'movie') + 's'
            if type_name not in new_results:
                new_results[type_name] = []

            new_results[type_name].append(r)

        # Combine movies, needs a cleaner way..
        if 'movies' in new_results:
            new_results['movies'] = self.combineOnIMDB(new_results['movies'])

        return new_results

    def combineOnIMDB(self, results):

        temp = {}
        order = []

        # Combine on imdb id
        for item in results:
            random_string = randomString()
            imdb = item.get('imdb', random_string)
            imdb = imdb if imdb else random_string

            if not temp.get(imdb):
                temp[imdb] = self.getLibraryTags(imdb)
                order.append(imdb)

            # Merge dicts
            temp[imdb] = mergeDicts(temp[imdb], item)

        # Make it a list again
        temp_list = [temp[x] for x in order]

        return temp_list

    def getLibraryTags(self, imdb):

        temp = {
            'in_wanted': False,
            'in_library': False,
        }

        # Add release info from current library
        db = get_db()
        try:

            media = None
            try:
                media = db.get('media', 'imdb-%s' % imdb, with_doc = True)['doc']
            except RecordNotFound:
                pass

            if media:

                if media.get('status') == 'active':
                    temp['in_wanted'] = media

                    try: temp['in_wanted']['profile'] = db.get('id', media['profile_id'])
                    except: temp['in_wanted']['profile'] = {'label': ''}

                for release in fireEvent('release.for_media', media['_id'], single = True):
                    if release.get('status') == 'done':
                        if not temp['in_library']:
                            temp['in_library'] = media
                            temp['in_library']['releases'] = []

                        temp['in_library']['releases'].append(release)
        except:
            log.error('Tried getting more info on searched movies: %s', traceback.format_exc())

        return temp

    def checkLibrary(self, result):

        result = mergeDicts(copy.deepcopy(self.default_info), copy.deepcopy(result))

        if result and result.get('imdb'):
            return mergeDicts(result, self.getLibraryTags(result['imdb']))
        return result
