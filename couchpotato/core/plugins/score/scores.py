from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.environment import Env
import re

name_scores = [
    # Tags
    'proper:15', 'repack:15', 'directors cut:15', 'extended:7', 'unrated:2',
    # Video
    'x264:1', 'h264:1',
    # Audio
    'DTS:4', 'AC3:2',
    # Quality
    '720p:10', '1080p:10', 'bluray:10', 'dvd:1', 'dvdrip:1', 'brrip:1', 'bdrip:1', 'bd50:1', 'bd25:1',
    # Language / Subs
    'german:-10', 'french:-10', 'spanish:-10', 'swesub:-20', 'danish:-10', 'dutch:-10',
    # Release groups
    'imbt:1', 'cocain:1', 'vomit:1', 'fico:1', 'arrow:1', 'pukka:1', 'prism:1', 'devise:1', 'esir:1', 'ctrlhd:1',
    'metis:1', 'diamond:1', 'wiki:1', 'cbgb:1', 'crossbow:1', 'sinners:1', 'amiable:1', 'refined:1', 'twizted:1', 'felony:1', 'hubris:1', 'machd:1',
    # Extras
    'extras:-40', 'trilogy:-40',
]

def nameScore(name, year):
    ''' Calculate score for words in the NZB name '''

    score = 0
    name = name.lower()

    # give points for the cool stuff
    for value in name_scores:
        v = value.split(':')
        add = int(v.pop())
        if v.pop() in name:
            score = score + add

    # points if the year is correct
    if str(year) in name:
        score = score + 5

    # Contains preferred word
    nzb_words = re.split('\W+', simplifyString(name))
    preferred_words = [x.strip() for x in Env.setting('preferred_words', section = 'searcher').split(',')]
    for word in preferred_words:
        if word.strip() and word.strip().lower() in nzb_words:
            score = score + 100

    return score

def nameRatioScore(nzb_name, movie_name):

    nzb_words = re.split('\W+', fireEvent('scanner.create_file_identifier', nzb_name, single = True))
    movie_words = re.split('\W+', simplifyString(movie_name))

    left_over = set(nzb_words) - set(movie_words)
    return 10 - len(left_over)


def sizeScore(size):
    return 0 if size else -20


def providerScore(provider):
    if provider in ['NZBMatrix', 'Nzbs', 'Newzbin']:
        return 30

    if provider in ['Newznab', 'Moovee', 'X264']:
        return 10

    return 0


def duplicateScore(nzb_name, movie_name):

    nzb_words = re.split('\W+', simplifyString(nzb_name))
    movie_words = re.split('\W+', simplifyString(movie_name))

    # minus for duplicates
    duplicates = [x for i, x in enumerate(nzb_words) if nzb_words[i:].count(x) > 1]

    return len(list(set(duplicates) - set(movie_words))) * -4
