from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.plugins.scanner.main import Scanner
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
    'metis:10', 'diamond:10', 'wiki:10', 'cbgb:10', 'crossbow:1', 'sinners:10', 'amiable:10', 'refined:1', 'twizted:1', 'felony:1', 'hubris:1', 'machd:1',
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


def namePositionScore(nzb_name, movie_name):
    score = 0

    nzb_words = re.split('\W+', simplifyString(nzb_name))
    qualities = fireEvent('quality.all', single = True)

    try:
        nzb_name = re.search(r'([\'"])[^\1]*\1', nzb_name).group(0)
    except:
        pass

    name_year = fireEvent('scanner.name_year', nzb_name, single = True)

    # Give points for movies beginning with the correct name
    name_split = simplifyString(nzb_name).split(simplifyString(movie_name))
    if name_split[0].strip() == '':
        score += 10

    # If year is second in line, give more points
    if len(name_split) > 1 and name_year:
        after_name = name_split[1].strip()
        if tryInt(after_name[:4]) == name_year.get('year', None):
            score += 10
            after_name = after_name[4:]

        # Give -point to crap between year and quality
        found_quality = None
        for quality in qualities:
            # Main in words
            if quality['identifier'] in nzb_words:
                found_quality = quality['identifier']

            # Alt in words
            for alt in quality['alternative']:
                if alt in nzb_words:
                    found_quality = alt
                    break

        if not found_quality:
            return score - 20

        allowed = []
        for value in name_scores:
            name, sc = value.split(':')
            allowed.append(name)

        inbetween = re.split('\W+', after_name.split(found_quality)[0].strip())

        score -= (10 * len(set(inbetween) - set(allowed)))

    return score


def sizeScore(size):
    return 0 if size else -20


def providerScore(provider):
    if provider in ['NZBMatrix', 'Nzbs', 'Newzbin']:
        return 20

    if provider in ['Newznab']:
        return 10

    return 0


def duplicateScore(nzb_name, movie_name):

    nzb_words = re.split('\W+', simplifyString(nzb_name))
    movie_words = re.split('\W+', simplifyString(movie_name))

    # minus for duplicates
    duplicates = [x for i, x in enumerate(nzb_words) if nzb_words[i:].count(x) > 1]

    return len(list(set(duplicates) - set(movie_words))) * -4


def partialIgnoredScore(nzb_name, movie_name):

    nzb_name = nzb_name.lower()
    movie_name = movie_name.lower()

    ignored_words = [x.strip().lower() for x in Env.setting('ignored_words', section = 'searcher').split(',')]

    score = 0
    for ignored_word in ignored_words:
        if ignored_word in nzb_name and ignored_word not in movie_name:
            score -= 5

    return score

def halfMultipartScore(nzb_name):

    wrong_found = 0
    for nr in [1, 2, 3, 4, 5, 'i', 'ii', 'iii', 'iv', 'v', 'a', 'b', 'c', 'd', 'e']:
        for wrong in ['cd', 'part', 'dis', 'disc', 'dvd']:
            if '%s%s' % (wrong, nr) in nzb_name.lower():
                wrong_found += 1

    if wrong_found == 1:
        return -30

    return 0
