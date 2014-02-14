from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.environment import Env
import re
import traceback

log = CPLog(__name__)


name_scores = [
    # Tags
    'proper:15', 'repack:15', 'directors cut:15', 'extended:7', 'unrated:2',
    # Video
    'x264:1', 'h264:1',
    # Audio
    'dts:4', 'ac3:2',
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


def nameScore(name, year, preferred_words):
    """ Calculate score for words in the NZB name """

    score = 0
    name = name.lower()

    # give points for the cool stuff
    for value in name_scores:
        v = value.split(':')
        add = int(v.pop())
        if v.pop() in name:
            score += add

    # points if the year is correct
    if str(year) in name:
        score += 5

    # Contains preferred word
    nzb_words = re.split('\W+', simplifyString(name))
    score += 100 * len(list(set(nzb_words) & set(preferred_words)))

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
    split_by = simplifyString(movie_name)
    name_split = []
    if len(split_by) > 0:
        name_split = simplifyString(nzb_name).split(split_by)
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

    try:
        score = tryInt(Env.setting('extra_score', section = provider.lower(), default = 0))
    except:
        score = 0

    return score


def duplicateScore(nzb_name, movie_name):

    nzb_words = re.split('\W+', simplifyString(nzb_name))
    movie_words = re.split('\W+', simplifyString(movie_name))

    # minus for duplicates
    duplicates = [x for i, x in enumerate(nzb_words) if nzb_words[i:].count(x) > 1]

    return len(list(set(duplicates) - set(movie_words))) * -4


def partialIgnoredScore(nzb_name, movie_name, ignored_words):

    nzb_name = nzb_name.lower()
    movie_name = movie_name.lower()

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


def sceneScore(nzb_name):

    check_names = [nzb_name]

    # Match names between "
    try: check_names.append(re.search(r'([\'"])[^\1]*\1', nzb_name).group(0))
    except: pass

    # Match longest name between []
    try: check_names.append(max(re.findall(r'[^[]*\[([^]]*)\]', nzb_name), key = len).strip())
    except: pass

    for name in check_names:

        # Strip twice, remove possible file extensions
        name = name.lower().strip(' "\'\.-_\[\]')
        name = re.sub('\.([a-z0-9]{0,4})$', '', name)
        name = name.strip(' "\'\.-_\[\]')

        # Make sure year and groupname is in there
        year = re.findall('(?P<year>19[0-9]{2}|20[0-9]{2})', name)
        group = re.findall('\-([a-z0-9]+)$', name)

        if len(year) > 0 and len(group) > 0:
            try:
                validate = fireEvent('release.validate', name, single = True)
                if validate and tryInt(validate.get('score')) != 0:
                    log.debug('Release "%s" scored %s, reason: %s', (nzb_name, validate['score'], validate['reasons']))
                    return tryInt(validate.get('score'))
            except:
                log.error('Failed scoring scene: %s', traceback.format_exc())

    return 0
