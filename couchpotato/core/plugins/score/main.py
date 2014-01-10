from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import getTitle, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.plugins.score.scores import nameScore, nameRatioScore, \
    sizeScore, providerScore, duplicateScore, partialIgnoredScore, namePositionScore, \
    halfMultipartScore, sceneScore
from couchpotato.environment import Env

log = CPLog(__name__)


class Score(Plugin):

    def __init__(self):
        addEvent('score.calculate', self.calculate)

    def calculate(self, nzb, movie):
        """ Calculate the score of a NZB, used for sorting later """

        # Merge global and category
        preferred_words = splitString(Env.setting('preferred_words', section = 'searcher').lower())
        try: preferred_words = list(set(preferred_words + splitString(movie['category']['preferred'].lower())))
        except: pass

        score = nameScore(toUnicode(nzb['name']), movie['library']['year'], preferred_words)

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

        # Merge global and category
        ignored_words = splitString(Env.setting('ignored_words', section = 'searcher').lower())
        try: ignored_words = list(set(ignored_words + splitString(movie['category']['ignored'].lower())))
        except: pass

        # Partial ignored words
        score += partialIgnoredScore(nzb['name'], getTitle(movie['library']), ignored_words)

        # Ignore single downloads from multipart
        score += halfMultipartScore(nzb['name'])

        # Extra provider specific check
        extra_score = nzb.get('extra_score')
        if extra_score:
            score += extra_score(nzb)

        # Scene / Nuke scoring
        score += sceneScore(nzb['name'])

        return score
