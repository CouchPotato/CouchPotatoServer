from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.environment import Env
import re

name_scores = [
    'proper:2', 'repack:2',
    'unrated:1',
    'x264:1',
    'DTS:4', 'AC3:2',
    '720p:10', '1080p:10', 'bluray:10', 'dvd:1', 'dvdrip:1', 'brrip:1', 'bdrip:1',
    'metis:1', 'diamond:1', 'wiki:1', 'CBGB:1',
    'german:-10', 'french:-10', 'spanish:-10', 'swesub:-20', 'danish:-10'
]

def nameScore(name, year):
    ''' Calculate score for words in the NZB name '''

    score = 0
    name = name.lower()

    #give points for the cool stuff
    for value in name_scores:
        v = value.split(':')
        add = int(v.pop())
        if v.pop() in name:
            score = score + add

    #points if the year is correct
    if str(year) in name:
        score = score + 1

    # Contains preferred word
    nzb_words = re.split('\W+', simplifyString(name))
    preferred_words = Env.setting('preferred_words', section = 'searcher').split(',')
    for word in preferred_words:
        if word.strip() and word.strip().lower() in nzb_words:
            score = score + 100

    return score

def nameRatioScore(nzb_name, movie_name):

    nzb_words = re.split('\W+', simplifyString(nzb_name))
    movie_words = re.split('\W+', simplifyString(movie_name))

    # Replace .,-_ with space
    left_over = len(nzb_words) - len(movie_words)
    if 2 <= left_over <= 6:
        return 4
    else:
        return 0
