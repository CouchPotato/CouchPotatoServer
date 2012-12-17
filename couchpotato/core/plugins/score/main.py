from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.plugins.score.scores import nameScore, nameRatioScore, \
    sizeScore, providerScore, duplicateScore, partialIgnoredScore, namePositionScore, \
    halfMultipartScore

log = CPLog(__name__)


class Score(Plugin):

    def __init__(self):
        addEvent('score.calculate', self.calculate)

    def calculate(self, nzb, movie):
        ''' Calculate the score of a NZB, used for sorting later '''

        score = nameScore(toUnicode(nzb['name']), movie['library']['year'])

        for movie_title in movie['library']['titles']:
            score += nameRatioScore(toUnicode(nzb['name']), toUnicode(movie_title['title']))
            score += namePositionScore(toUnicode(nzb['name']), toUnicode(movie_title['title']))

        score += sizeScore(nzb['size'])

        # Torrents only
        if nzb.get('seeders'):
            try:
                score += nzb.get('seeders') / 5
                score += nzb.get('leechers') / 10
            except:
                pass

        # Provider score
        score += providerScore(nzb['provider'])

        # Duplicates in name
        score += duplicateScore(nzb['name'], getTitle(movie['library']))

        # Partial ignored words
        score += partialIgnoredScore(nzb['name'], getTitle(movie['library']))

        # Ignore single downloads from multipart
        score += halfMultipartScore(nzb['name'])

        # Extra provider specific check
        extra_score = nzb.get('extra_score')
        if extra_score:
            score += extra_score(nzb)

        return score
