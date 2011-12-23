#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2011 Nicolas Wack <wackou@gmail.com>
#
# GuessIt is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# GuessIt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from guessit import fileutils, textutils
from guessit.guess import Guess, merge_similar_guesses, merge_all, choose_int, choose_string
from guessit.date import search_date, search_year
from guessit.language import search_language
from guessit.patterns import video_exts, subtitle_exts, sep, deleted, video_rexps, websites, episode_rexps, weak_episode_rexps, non_episode_title, properties, canonical_form
from guessit.matchtree import get_group, find_group, leftover_valid_groups, tree_to_string
from guessit.textutils import find_first_level_groups, split_on_groups, blank_region, clean_string, to_utf8
from guessit.fileutils import split_path_components
import datetime
import os.path
import re
import copy
import logging

log = logging.getLogger("guessit.matcher")



def split_explicit_groups(string):
    """return the string split into explicit groups, that is, those either
    between parenthese, square brackets or curly braces, and those separated
    by a dash."""
    result = find_first_level_groups(string, '()')
    result = reduce(lambda l, x: l + find_first_level_groups(x, '[]'), result, [])
    result = reduce(lambda l, x: l + find_first_level_groups(x, '{}'), result, [])
    # do not do this at this moment, it is not strong enough and can break other
    # patterns, such as dates, etc...
    #result = reduce(lambda l, x: l + x.split('-'), result, [])

    return result


def format_guess(guess):
    """Format all the found values to their natural type.
    For instance, a year would be stored as an int value, etc...

    Note that this modifies the dictionary given as input.
    """
    for prop, value in guess.items():
        if prop in ('season', 'episodeNumber', 'year', 'cdNumber', 'cdNumberTotal'):
            guess[prop] = int(guess[prop])
        elif isinstance(value, basestring):
            if prop in ('edition',):
                value = clean_string(value)
            guess[prop] = canonical_form(value)

    return guess


def guess_groups(string, result, filetype):
    # add sentinels so we can match a separator char at either end of
    # our groups, even when they are at the beginning or end of the string
    # we will adjust the span accordingly later
    #
    # filetype can either be movie, moviesubtitle, episode, episodesubtitle
    current = ' ' + string + ' '

    regions = [] # list of (start, end) of matched regions

    def guessed(match_dict, confidence):
        guess = format_guess(Guess(match_dict, confidence = confidence))
        result.append(guess)
        log.debug('Found with confidence %.2f: %s' % (confidence, guess))
        return guess

    def update_found(string, guess, span, span_adjust = (0,0)):
        span = (span[0] + span_adjust[0],
                span[1] + span_adjust[1])
        regions.append((span, guess))
        return blank_region(string, span)

    # try to find dates first, as they are very specific
    date, span = search_date(current)
    if date:
        guess = guessed({ 'date': date }, confidence = 1.0)
        current = update_found(current, guess, span)

    # for non episodes only, look for year information
    if filetype not in ('episode', 'episodesubtitle'):
        year, span = search_year(current)
        if year:
            guess = guessed({ 'year': year }, confidence = 1.0)
            current = update_found(current, guess, span)

    # specific regexps (ie: cd number, season X episode, ...)
    for rexp, confidence, span_adjust in video_rexps:
        match = re.search(rexp, current, re.IGNORECASE)
        if match:
            metadata = match.groupdict()
            # is this the better place to put it? (maybe, as it is at least the soonest that we can catch it)
            if 'cdNumberTotal' in metadata and metadata['cdNumberTotal'] is None:
                del metadata['cdNumberTotal']

            guess = guessed(metadata, confidence = confidence)
            current = update_found(current, guess, match.span(), span_adjust)

    if filetype in ('episode', 'episodesubtitle'):
        for rexp, confidence, span_adjust in episode_rexps:
            match = re.search(rexp, current, re.IGNORECASE)
            if match:
                metadata = match.groupdict()
                guess = guessed(metadata, confidence = confidence)
                current = update_found(current, guess, match.span(), span_adjust)


    # Now websites, but as exact string instead of regexps
    clow = current.lower()
    for site in websites:
        pos = clow.find(site.lower())
        if pos != -1:
            guess = guessed({ 'website': site }, confidence = confidence)
            current = update_found(current, guess, (pos, pos+len(site)))
            clow = current.lower()


    # release groups have certain constraints, cannot be included in the previous general regexps
    group_names = [ r'\.(Xvid)-(?P<releaseGroup>.*?)[ \.]',
                    r'\.(DivX)-(?P<releaseGroup>.*?)[\. ]',
                    r'\.(DVDivX)-(?P<releaseGroup>.*?)[\. ]',
                    ]
    for rexp in group_names:
        match = re.search(rexp, current, re.IGNORECASE)
        if match:
            metadata = match.groupdict()
            metadata.update({ 'videoCodec': match.group(1) })
            guess = guessed(metadata, confidence = 0.8)
            current = update_found(current, guess, match.span(), span_adjust = (1, -1))


    # common well-defined words and regexps
    clow = current.lower()
    confidence = 1.0 # for all of them
    for prop, values in properties.items():
        for value in values:
            pos = clow.find(value.lower())
            if pos != -1:
                end = pos + len(value)
                # make sure our word is always surrounded by separators
                if clow[pos-1] not in sep or clow[end] not in sep:
                    # note: sep is a regexp, but in this case using it as
                    #       a sequence achieves the same goal
                    continue

                guess = guessed({ prop: value }, confidence = confidence)
                current = update_found(current, guess, (pos, end))
                clow = current.lower()

    # weak guesses for episode number, only run it if we don't have an estimate already
    if filetype in ('episode', 'episodesubtitle'):
        if not any('episodeNumber' in match for match in result):
            for rexp, _, span_adjust in weak_episode_rexps:
                match = re.search(rexp, current, re.IGNORECASE)
                if match:
                    metadata = match.groupdict()
                    epnum = int(metadata['episodeNumber'])
                    if epnum > 100:
                        guess = guessed({ 'season': epnum // 100,
                                          'episodeNumber': epnum % 100 }, confidence = 0.6)
                    else:
                        guess = guessed(metadata, confidence = 0.3)
                    current = update_found(current, guess, match.span(), span_adjust)

    # try to find languages now
    language, span, confidence = search_language(current)
    while language:
        # is it a subtitle language?
        if 'sub' in clean_string(current[:span[0]]).lower().split(' '):
            guess = guessed({ 'subtitleLanguage': language }, confidence = confidence)
        else:
            guess = guessed({ 'language': language }, confidence = confidence)
        current = update_found(current, guess, span)

        language, span, confidence = search_language(current)


    # remove our sentinels now and ajust spans accordingly
    assert(current[0] == ' ' and current[-1] == ' ')
    current = current[1:-1]
    regions = [ ((start-1, end-1), guess) for (start, end), guess in regions ]

    # split into '-' separated subgroups (with required separator chars
    # around the dash)
    didx = current.find('-')
    while didx > 0:
        regions.append(((didx, didx), None))
        didx = current.find('-', didx+1)

    # cut our final groups, and rematch the guesses to the group that created
    # id, None if it is a leftover group
    region_spans = [ span for span, guess in regions ]
    string_groups = split_on_groups(string, region_spans)
    remaining_groups = split_on_groups(current, region_spans)
    guesses = []

    pos = 0
    for group in string_groups:
        found = False
        for span, guess in regions:
            if span[0] == pos:
                guesses.append(guess)
                found = True
        if not found:
            guesses.append(None)

        pos += len(group)

    return  zip(string_groups,
                remaining_groups,
                guesses)


def match_from_epnum_position(match_tree, epnum_pos, guessed, update_found):
    """guessed is a callback function to call with the guessed group
    update_found is a callback to update the match group and returns leftover groups."""
    pidx, eidx, gidx = epnum_pos

    # a few helper functions to be able to filter using high-level semantics
    def same_pgroup_before(group):
        _, (ppidx, eeidx, ggidx) = group
        return ppidx == pidx and (eeidx, ggidx) < (eidx, gidx)

    def same_pgroup_after(group):
        _, (ppidx, eeidx, ggidx) = group
        return ppidx == pidx and (eeidx, ggidx) > (eidx, gidx)

    def same_egroup_before(group):
        _, (ppidx, eeidx, ggidx) = group
        return ppidx == pidx and eeidx == eidx and ggidx < gidx

    def same_egroup_after(group):
        _, (ppidx, eeidx, ggidx) = group
        return ppidx == pidx and eeidx == eidx and ggidx > gidx

    leftover = leftover_valid_groups(match_tree)

    # if we have at least 1 valid group before the episodeNumber, then it's probably
    # the series name
    series_candidates = filter(same_pgroup_before, leftover)
    if len(series_candidates) >= 1:
        guess = guessed({ 'series': series_candidates[0][0] }, confidence = 0.7)
        leftover = update_found(leftover, series_candidates[0][1], guess)

    # only 1 group after (in the same path group) and it's probably the episode title
    title_candidates = filter(lambda g:g[0].lower() not in non_episode_title,
                              filter(same_pgroup_after, leftover))
    if len(title_candidates) == 1:
        guess = guessed({ 'title': title_candidates[0][0] }, confidence = 0.5)
        leftover = update_found(leftover, title_candidates[0][1], guess)
    else:
        # try in the same explicit group, with lower confidence
        title_candidates = filter(lambda g:g[0].lower() not in non_episode_title,
                                  filter(same_egroup_after, leftover))
        if len(title_candidates) == 1:
            guess = guessed({ 'title': title_candidates[0][0] }, confidence = 0.4)
            leftover = update_found(leftover, title_candidates[0][1], guess)

    # epnumber is the first group and there are only 2 after it in same path group
    #  -> season title - episode title
    already_has_title = (find_group(match_tree, 'title') != [])

    title_candidates = filter(lambda g:g[0].lower() not in non_episode_title,
                              filter(same_pgroup_after, leftover))
    if (not already_has_title and                    # no title
        not filter(same_pgroup_before, leftover) and # no groups before
        len(title_candidates) == 2):                 # only 2 groups after

        guess = guessed({ 'series': title_candidates[0][0] }, confidence = 0.4)
        leftover = update_found(leftover, title_candidates[0][1], guess)
        guess = guessed({ 'title': title_candidates[1][0] }, confidence = 0.4)
        leftover = update_found(leftover, title_candidates[1][1], guess)


    # if we only have 1 remaining valid group in the pathpart before the filename,
    # then it's likely that it is the series name
    series_candidates = [ group for group in leftover if group[1][0] == pidx-1 ]
    if len(series_candidates) == 1:
        guess = guessed({ 'series': series_candidates[0][0] }, confidence = 0.5)
        leftover = update_found(leftover, series_candidates[0][1], guess)

    return match_tree



class IterativeMatcher(object):
    def __init__(self, filename, filetype = 'autodetect'):
        """An iterative matcher tries to match different patterns that appear
        in the filename.

        The 'filetype' argument indicates which type of file you want to match.
        If it is 'autodetect', the matcher will try to see whether it can guess
        that the file corresponds to an episode, or otherwise will assume it is
        a movie.

        The recognized 'filetype' values are:
        [ autodetect, subtitle, movie, moviesubtitle, episode, episodesubtitle ]


        The IterativeMatcher works mainly in 2 steps:

        First, it splits the filename into a match_tree, which is a tree of groups
        which have a semantic meaning, such as episode number, movie title,
        etc...

        The match_tree created looks like the following:

        0000000000000000000000000000000000000000000000000000000000000000000000000000000000 111
        0000011111111111112222222222222233333333444444444444444455555555666777777778888888 000
        0000000000000000000000000000000001111112011112222333333401123334000011233340000000 000
        __________________(The.Prestige).______.[____.HP.______.{__-___}.St{__-___}.Chaps].___
        xxxxxttttttttttttt               ffffff  vvvv    xxxxxx  ll lll     xx xxx         ccc
        [XCT].Le.Prestige.(The.Prestige).DVDRip.[x264.HP.He-Aac.{Fr-Eng}.St{Fr-Eng}.Chaps].mkv

        The first 3 lines indicates the group index in which a char in the
        filename is located. So for instance, x264 is the group (0, 4, 1), and
        it corresponds to a video codec, denoted by the letter'v' in the 4th line.
        (for more info, see guess.matchtree.tree_to_string)


         Second, it tries to merge all this information into a single object
         containing all the found properties, and does some (basic) conflict
         resolution when they arise.
        """

        if filetype not in ('autodetect', 'subtitle', 'movie', 'moviesubtitle',
                            'episode', 'episodesubtitle'):
            raise ValueError, "filetype needs to be one of ('autodetect', 'subtitle', 'movie', 'moviesubtitle', 'episode', 'episodesubtitle')"
        if not isinstance(filename, unicode):
            log.debug('WARNING: given filename to matcher is not unicode...')

        match_tree = []
        result = [] # list of found metadata

        def guessed(match_dict, confidence):
            guess = format_guess(Guess(match_dict, confidence = confidence))
            result.append(guess)
            log.debug('Found with confidence %.2f: %s' % (confidence, guess))
            return guess

        def update_found(leftover, group_pos, guess):
            pidx, eidx, gidx = group_pos
            group = match_tree[pidx][eidx][gidx]
            match_tree[pidx][eidx][gidx] = (group[0],
                                            deleted * len(group[0]),
                                            guess)
            return [ g for g in leftover if g[1] != group_pos ]


        # 1- first split our path into dirs + basename + ext
        match_tree = split_path_components(filename)

        fileext = match_tree.pop(-1)[1:].lower()
        if fileext in subtitle_exts:
            if 'movie' in filetype:
                filetype = 'moviesubtitle'
            elif 'episode' in filetype:
                filetype = 'episodesubtitle'
            else:
                filetype = 'subtitle'
            extguess = guessed({ 'container': fileext }, confidence = 1.0)
        elif fileext in video_exts:
            extguess = guessed({ 'container': fileext }, confidence = 1.0)
        else:
            extguess = guessed({ 'extension':  fileext}, confidence = 1.0)

        # TODO: depending on the extension, we could already grab some info and maybe specialized
        #       guessers, eg: a lang parser for idx files, an automatic detection of the language
        #       for srt files, a video metadata extractor for avi, mkv, ...

        # if we are on autodetect, try to do it now so we can tell the
        # guess_groups function what type of info it should be looking for
        if filetype in ('autodetect', 'subtitle'):
            for rexp, confidence, span_adjust in episode_rexps:
                match = re.search(rexp, filename, re.IGNORECASE)
                if match:
                    if filetype == 'autodetect':
                        filetype = 'episode'
                    elif filetype == 'subtitle':
                        filetype = 'episodesubtitle'
                    break

            # if no episode info found, assume it's a movie
            if filetype == 'autodetect':
                filetype = 'movie'
            elif filetype == 'subtitle':
                filetype = 'moviesubtitle'

        guessed({ 'type': filetype }, confidence = 1.0)


        # 2- split each of those into explicit groups, if any
        # note: be careful, as this might split some regexps with more confidence such as
        #       Alfleni-Team, or [XCT] or split a date such as (14-01-2008)
        match_tree = [ split_explicit_groups(part) for part in match_tree ]


        # 3- try to match information in decreasing order of confidence and
        #    blank the matching group in the string if we found something
        for pathpart in match_tree:
            for gidx, explicit_group in enumerate(pathpart):
                pathpart[gidx] = guess_groups(explicit_group, result, filetype = filetype)

        # 4- try to identify the remaining unknown groups by looking at their position
        #    relative to other known elements

        if filetype in ('episode', 'episodesubtitle'):
            eps = find_group(match_tree, 'episodeNumber')
            if eps:
                match_tree = match_from_epnum_position(match_tree, eps[0], guessed, update_found)

            leftover = leftover_valid_groups(match_tree)

            if not eps:
                # if we don't have the episode number, but at least 2 groups in the
                # last path group, then it's probably series - eptitle
                title_candidates = filter(lambda g:g[0].lower() not in non_episode_title,
                                          filter(lambda g: g[1][0] == len(match_tree)-1,
                                                 leftover_valid_groups(match_tree)))
                if len(title_candidates) >= 2:
                    guess = guessed({ 'series': title_candidates[0][0] }, confidence = 0.4)
                    leftover = update_found(leftover, title_candidates[0][1], guess)
                    guess = guessed({ 'title': title_candidates[1][0] }, confidence = 0.4)
                    leftover = update_found(leftover, title_candidates[1][1], guess)


            # if there's a path group that only contains the season info, then the previous one
            # is most likely the series title (ie: .../series/season X/...)
            eps = [ gpos for gpos in find_group(match_tree, 'season')
                    if 'episodeNumber' not in get_group(match_tree, gpos)[2] ]

            if eps:
                pidx, eidx, gidx = eps[0]
                previous = [ group for group in leftover if group[1][0] == pidx - 1 ]
                if len(previous) == 1:
                    guess = guessed({ 'series': previous[0][0] }, confidence = 0.5)
                    leftover = update_found(leftover, previous[0][1], guess)


        elif filetype in ('movie', 'moviesubtitle'):
            leftover_all = leftover_valid_groups(match_tree)

            # specific cases:
            #  - movies/tttttt (yyyy)/tttttt.ccc
            try:
                if match_tree[-3][0][0][0].lower() == 'movies':
                    # Note:too generic, might solve all the unittests as they all contain 'movies'
                    # in their path
                    #
                    #if len(match_tree[-2][0]) == 1:
                    #    title = match_tree[-2][0][0]
                    #    guess = guessed({ 'title': clean_string(title[0]) }, confidence = 0.7)
                    #    update_found(leftover_all, title, guess)

                    year_group = filter(lambda gpos: gpos[0] == len(match_tree)-2,
                                        find_group(match_tree, 'year'))[0]
                    leftover = leftover_valid_groups(match_tree,
                                                     valid = lambda g: ((g[0] and g[0][0] not in sep) and
                                                                        g[1][0] == len(match_tree) - 2))
                    if len(match_tree[-2]) == 2 and year_group[1] == 1:
                        title = leftover[0]
                        guess = guessed({ 'title': clean_string(title[0]) },
                                        confidence = 0.8)
                        update_found(leftover_all, title[1], guess)
                        raise Exception # to exit the try catch now

                    leftover = [ g for g in leftover_all if (g[1][0] == year_group[0] and
                                                             g[1][1] < year_group[1] and
                                                             g[1][2] < year_group[2]) ]
                    leftover = sorted(leftover, key = lambda x:x[1])
                    title = leftover[0]
                    guess = guessed({ 'title': title[0] }, confidence = 0.8)
                    leftover = update_found(leftover, title[1], guess)
            except:
                pass

            # if we have either format or videoCodec in the folder containing the file
            # or one of its parents, then we should probably look for the title in
            # there rather than in the basename
            props = filter(lambda g: g[0] <= len(match_tree) - 2,
                           find_group(match_tree, 'videoCodec') +
                           find_group(match_tree, 'format') +
                           find_group(match_tree, 'language'))
            leftover = None
            if props and all(g[0] == props[0][0] for g in props):
                leftover = [ g for g in leftover_all if g[1][0] == props[0][0] ]

            if props and leftover:
                guess = guessed({ 'title': leftover[0][0] }, confidence = 0.7)
                leftover = update_found(leftover, leftover[0][1], guess)

            else:
                # first leftover group in the last path part sounds like a good candidate for title,
                # except if it's only one word and that the first group before has at least 3 words in it
                # (case where the filename contains an 8 chars short name and the movie title is
                #  actually in the parent directory name)
                leftover = [ g for g in leftover_all if g[1][0] == len(match_tree)-1 ]
                if leftover:
                    title, (pidx, eidx, gidx) = leftover[0]
                    previous_pgroup_leftover = filter(lambda g: g[1][0] == pidx-1, leftover_all)

                    if (title.count(' ') == 0 and
                        previous_pgroup_leftover and
                        previous_pgroup_leftover[0][0].count(' ') >= 2):

                        guess = guessed({ 'title': previous_pgroup_leftover[0][0] }, confidence = 0.6)
                        leftover = update_found(leftover, previous_pgroup_leftover[0][1], guess)

                    else:
                        guess = guessed({ 'title': title }, confidence = 0.6)
                        leftover = update_found(leftover, leftover[0][1], guess)
                else:
                    # if there were no leftover groups in the last path part, look in the one before that
                    previous_pgroup_leftover = filter(lambda g: g[1][0] == len(match_tree)-2, leftover_all)
                    if previous_pgroup_leftover:
                        guess = guessed({ 'title': previous_pgroup_leftover[0][0] }, confidence = 0.6)
                        leftover = update_found(leftover, previous_pgroup_leftover[0][1], guess)






        # 5- perform some post-processing steps

        # 5.1- try to promote language to subtitle language where it makes sense
        for pidx, eidx, gidx in find_group(match_tree, 'language'):
            string, remaining, guess = get_group(match_tree, (pidx, eidx, gidx))

            def promote_subtitle():
                guess.set('subtitleLanguage', guess['language'], confidence = guess.confidence('language'))
                del guess['language']

            # - if we matched a language in a file with a sub extension and that the group
            #   is the last group of the filename, it is probably the language of the subtitle
            #   (eg: 'xxx.english.srt')
            if (fileext in subtitle_exts and
                pidx == len(match_tree) - 1 and
                eidx == len(match_tree[pidx]) - 1):
                promote_subtitle()

            # - if a language is in an explicit group just preceded by "st", it is a subtitle
            #   language (eg: '...st[fr-eng]...')
            if eidx > 0:
                previous = get_group(match_tree, (pidx, eidx-1, -1))
                if previous[0][-2:].lower() == 'st':
                    promote_subtitle()



        # re-append the extension now
        match_tree.append([[(fileext, deleted*len(fileext), extguess)]])

        self.parts = result
        self.match_tree = match_tree

        if filename.startswith('/'):
            filename = ' ' + filename

        log.debug('Found match tree:\n%s\n%s' % (to_utf8(tree_to_string(match_tree)),
                                                 to_utf8(filename)))


    def matched(self):
        # we need to make a copy here, as the merge functions work in place and
        # calling them on the match tree would modify it
        parts = copy.deepcopy(self.parts)

        # 1- start by doing some common preprocessing tasks

        # 1.1- ", the" at the end of a series title should be prepended to it
        for part in parts:
            if 'series' not in part:
                continue

            series = part['series']
            lseries = series.lower()

            if lseries[-4:] == ',the':
                part['series'] = 'The ' + series[:-4]

            if lseries[-5:] == ', the':
                part['series'] = 'The ' + series[:-5]


        # 2- try to merge similar information together and give it a higher confidence
        for int_part in ('year', 'season', 'episodeNumber'):
            merge_similar_guesses(parts, int_part, choose_int)

        for string_part in ('title', 'series', 'container', 'format', 'releaseGroup', 'website',
                            'audioCodec', 'videoCodec', 'screenSize', 'episodeFormat'):
            merge_similar_guesses(parts, string_part, choose_string)

        result = merge_all(parts, append = ['language', 'subtitleLanguage', 'other'])

        # 3- some last minute post-processing
        if (result['type'] == 'episode' and
            'season' not in result and
            result.get('episodeFormat', '') == 'Minisode'):
            result['season'] = 0

        log.debug('Final result: ' + result.nice_string())
        return result
