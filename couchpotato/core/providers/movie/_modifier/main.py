from couchpotato.core.event import addEvent
from couchpotato.core.helpers.variable import mergeDicts
from couchpotato.core.plugins.base import Plugin


class MovieResultModifier(Plugin):

    def __init__(self):
        addEvent('result.modify.movie.search', self.combineOnIMDB)


    def combineOnIMDB(self, results):

        temp = {}
        unique = 1

        # Combine on imdb id
        for item in results:
            imdb = item.get('imdb')
            if imdb:
                if not temp.get(imdb):
                    temp[imdb] = {}

                # Merge dicts
                temp[imdb] = mergeDicts(temp[imdb], item)
            else:
                temp[unique] = item
                unique += 1

        # Make it a list again
        temp_list = [temp[x] for x in temp]

        return temp_list
