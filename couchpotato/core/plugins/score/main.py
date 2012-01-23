from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.plugins.score.scores import nameScore, nameRatioScore, \
    sizeScore

log = CPLog(__name__)


class Score(Plugin):

    def __init__(self):
        addEvent('score.calculate', self.calculate)

    def calculate(self, nzb, movie):
        ''' Calculate the score of a NZB, used for sorting later '''

        score = nameScore(toUnicode(nzb['name']), movie['library']['year'])

        for movie_title in movie['library']['titles']:
            score += nameRatioScore(nzb['name'], movie_title['title'])

        score += sizeScore(nzb['size'])

        return score
