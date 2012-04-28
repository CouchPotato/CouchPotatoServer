# -*- coding: utf-8 -*-
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
from . import ServiceBase
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..videos import Episode, Movie, UnknownVideo
import logging


logger = logging.getLogger(__name__)


class TheSubDB(ServiceBase):
    server_url = 'http://api.thesubdb.com/'  # for testing purpose, use http://sandbox.thesubdb.com/ instead
    user_agent = 'SubDB/1.0 (subliminal/0.5; https://github.com/Diaoul/subliminal)'  # defined by the API
    api_based = True
    languages = {'af': 'af', 'cs': 'cs', 'da': 'da', 'de': 'de', 'en': 'en', 'es': 'es', 'fi': 'fi',
                 'fr': 'fr', 'hu': 'hu', 'id': 'id', 'it': 'it', 'la': 'la', 'nl': 'nl', 'no': 'no',
                 'oc': 'oc', 'pl': 'pl', 'pt': 'pt', 'ro': 'ro', 'ru': 'ru', 'sl': 'sl', 'sr': 'sr',
                 'sv': 'sv', 'tr': 'tr'}  # list available with the API at http://sandbox.thesubdb.com/?action=languages
    reverted_languages = False
    videos = [Movie, Episode, UnknownVideo]
    require_video = True

    def list(self, video, languages):
        if not self.check_validity(video, languages):
            return []
        results = self.query(video.path, video.hashes['TheSubDB'], languages)
        return results

    def query(self, filepath, moviehash, languages):
        r = self.session.get(self.server_url, params={'action': 'search', 'hash': moviehash})
        if r.status_code == 404:
            logger.debug(u'Could not find subtitles for hash %s' % moviehash)
            return []
        if r.status_code != 200:
            logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
            return []
        available_languages = set([self.get_revert_language(l) for l in r.content.split(',')])
        languages &= available_languages
        if not languages:
            logger.debug(u'Could not find subtitles for hash %s with languages %r (only %r available)' % (moviehash, languages, available_languages))
            return []
        subtitles = []
        for language in languages:
            path = get_subtitle_path(filepath, language, self.config.multi)
            subtitle = ResultSubtitle(path, language, service=self.__class__.__name__.lower(), link='%s?action=download&hash=%s&language=%s' % (self.server_url, moviehash, self.get_language(language)))
            subtitles.append(subtitle)
        return subtitles

Service = TheSubDB
