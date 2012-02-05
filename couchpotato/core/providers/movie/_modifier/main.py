from couchpotato import get_session
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import mergeDicts
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
        unique = 1

        # Combine on imdb id
        for item in results:
            imdb = item.get('imdb')
            if imdb:
                if not temp.get(imdb):
                    temp[imdb] = self.getLibraryTags(imdb)

                # Merge dicts
                temp[imdb] = mergeDicts(temp[imdb], item)
            else:
                temp[unique] = item
                unique += 1

        # Make it a list again
        temp_list = [temp[x] for x in temp]

        return temp_list

    def getLibraryTags(self, imdb):

        temp = {
            'in_wanted': False,
            'in_library': False,
        }

        # Add release info from current library
        try:
            db = get_session()
            l = db.query(Library).filter_by(identifier = imdb).first()
            if l:

                # Statuses
                active_status = fireEvent('status.get', 'active', single = True)
                done_status = fireEvent('status.get', 'done', single = True)

                for movie in l.movies:
                    if movie.status_id == active_status['id']:
                        temp['in_wanted'] = movie.profile.to_dict()

                    for release in movie.releases:
                        if release.status_id == done_status['id']:
                            temp['in_library'] = release.quality.to_dict()
        except:
            log.error('Tried getting more info on searched movies: %s' % traceback.format_exc())

        return temp

    def checkLibrary(self, result):
        if result and result.get('imdb'):
            return mergeDicts(result, self.getLibraryTags(result['imdb']))
        return result
