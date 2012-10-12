from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import mergeDicts, randomString
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Library
import traceback

log = CPLog(__name__)


class MovieResultModifier(Plugin):

    def __init__(self):
        addEvent('result.modify.movie.search', self.combineOnIMDB)
        addEvent('result.modify.movie.info', self.checkLibrary)

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

            if item.get('via_imdb'):
                if order.count(imdb):
                    order.remove(imdb)
                order.insert(0, imdb)

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
        db = get_session()
        try:
            l = db.query(Library).filter_by(identifier = imdb).first()
            if l:

                # Statuses
                active_status = fireEvent('status.get', 'active', single = True)
                done_status = fireEvent('status.get', 'done', single = True)

                for movie in l.movies:
                    if movie.status_id == active_status['id']:
                        temp['in_wanted'] = fireEvent('movie.get', movie.id, single = True)

                    for release in movie.releases:
                        if release.status_id == done_status['id']:
                            temp['in_library'] = fireEvent('movie.get', movie.id, single = True)
        except:
            log.error('Tried getting more info on searched movies: %s', traceback.format_exc())

        return temp

    def checkLibrary(self, result):
        if result and result.get('imdb'):
            return mergeDicts(result, self.getLibraryTags(result['imdb']))
        return result
