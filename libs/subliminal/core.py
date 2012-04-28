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
from .exceptions import DownloadFailedError
from .services import ServiceConfig
from .tasks import DownloadTask, ListTask
from .utils import get_keywords
from .videos import Episode, Movie, scan
from collections import defaultdict
from itertools import groupby
import guessit
import logging


__all__ = ['SERVICES', 'LANGUAGE_INDEX', 'SERVICE_INDEX', 'SERVICE_CONFIDENCE', 'MATCHING_CONFIDENCE',
           'create_list_tasks', 'create_download_tasks', 'consume_task', 'matching_confidence',
           'key_subtitles', 'group_by_video']
logger = logging.getLogger(__name__)
SERVICES = ['opensubtitles', 'bierdopje', 'subswiki', 'subtitulos', 'thesubdb']
LANGUAGE_INDEX, SERVICE_INDEX, SERVICE_CONFIDENCE, MATCHING_CONFIDENCE = range(4)


def create_list_tasks(paths, languages, services, force, multi, cache_dir, max_depth):
    """Create a list of :class:`~subliminal.tasks.ListTask` from one or more paths using the given criteria

    :param paths: path(s) to video file or folder
    :type paths: string or list
    :param set languages: languages to search for
    :param list services: services to use for the search
    :param bool force: force searching for subtitles even if some are detected
    :param bool multi: search multiple languages for the same video
    :param string cache_dir: path to the cache directory to use
    :param int max_depth: maximum depth for scanning entries
    :return: the created tasks
    :rtype: list of :class:`~subliminal.tasks.ListTask`

    """
    scan_result = []
    for p in paths:
        scan_result.extend(scan(p, max_depth))
    logger.debug(u'Found %d videos in %r with maximum depth %d' % (len(scan_result), paths, max_depth))
    tasks = []
    config = ServiceConfig(multi, cache_dir)
    for video, detected_subtitles in scan_result:
        detected_languages = set([s.language for s in detected_subtitles])
        wanted_languages = languages.copy()
        if not force and multi:
            wanted_languages -= detected_languages
            if not wanted_languages:
                logger.debug(u'No need to list multi subtitles %r for %r because %r detected' % (languages, video, detected_languages))
                continue
        if not force and not multi and None in detected_languages:
            logger.debug(u'No need to list single subtitles %r for %r because one detected' % (languages, video))
            continue
        logger.debug(u'Listing subtitles %r for %r with services %r' % (wanted_languages, video, services))
        for service_name in services:
            mod = __import__('services.' + service_name, globals=globals(), locals=locals(), fromlist=['Service'], level=-1)
            service = mod.Service
            service_languages = wanted_languages & service.available_languages()
            if not service_languages:
                logger.debug(u'Skipping %r: none of wanted languages %r available for service %s' % (video, wanted_languages, service_name))
                continue
            if not service.is_valid_video(video):
                logger.debug(u'Skipping %r: not part of supported videos %r for service %s' % (video, service.videos, service_name))
                continue
            task = ListTask(video, service_languages, service_name, config)
            logger.debug(u'Created task %r' % task)
            tasks.append(task)
    return tasks


def create_download_tasks(subtitles_by_video, multi):
    """Create a list of :class:`~subliminal.tasks.DownloadTask` from a list results grouped by video

    :param subtitles_by_video: :class:`~subliminal.tasks.ListTask` results grouped by video and sorted
    :type subtitles_by_video: dict of :class:`~subliminal.videos.Video` => [:class:`~subliminal.subtitles.Subtitle`]
    :param order: preferred order for subtitles sorting
    :type list: list of :data:`LANGUAGE_INDEX`, :data:`SERVICE_INDEX`, :data:`SERVICE_CONFIDENCE`, :data:`MATCHING_CONFIDENCE`
    :param bool multi: download multiple languages for the same video
    :return: the created tasks
    :rtype: list of :class:`~subliminal.tasks.DownloadTask`

    """
    tasks = []
    for video, subtitles in subtitles_by_video.iteritems():
        if not subtitles:
            continue
        if not multi:
            task = DownloadTask(video, list(subtitles))
            logger.debug(u'Created task %r' % task)
            tasks.append(task)
            continue
        for _, by_language in groupby(subtitles, lambda s: s.language):
            task = DownloadTask(video, list(by_language))
            logger.debug(u'Created task %r' % task)
            tasks.append(task)
    return tasks


def consume_task(task, services=None):
    """Consume a task. If the ``services`` parameter is given, the function will attempt
    to get the service from it. In case the service is not in ``services``, it will be initialized
    and put in ``services``

    :param task: task to consume
    :type task: :class:`~subliminal.tasks.ListTask` or :class:`~subliminal.tasks.DownloadTask`
    :param dict services: mapping between the service name and an instance of this service
    :return: the result of the task
    :rtype: list of :class:`~subliminal.subtitles.ResultSubtitle` or :class:`~subliminal.subtitles.Subtitle`

    """
    if services is None:
        services = {}
    logger.info(u'Consuming %r' % task)
    result = None
    if isinstance(task, ListTask):
        if task.service not in services:
            mod = __import__('services.' + task.service, globals=globals(), locals=locals(), fromlist=['Service'], level=-1)
            services[task.service] = mod.Service(task.config)
            services[task.service].init()
        subtitles = services[task.service].list(task.video, task.languages)
        result = subtitles
    elif isinstance(task, DownloadTask):
        for subtitle in task.subtitles:
            if subtitle.service not in services:
                mod = __import__('services.' + subtitle.service, globals=globals(), locals=locals(), fromlist=['Service'], level=-1)
                services[subtitle.service] = mod.Service()
                services[subtitle.service].init()
            try:
                services[subtitle.service].download(subtitle)
                result = subtitle
                break
            except DownloadFailedError:
                logger.warning(u'Could not download subtitle %r, trying next' % subtitle)
                continue
        if result is None:
            logger.error(u'No subtitles could be downloaded for video %r' % task.video)
    return result


def matching_confidence(video, subtitle):
    """Compute the probability (confidence) that the subtitle matches the video

    :param video: video to match
    :type video: :class:`~subliminal.videos.Video`
    :param subtitle: subtitle to match
    :type subtitle: :class:`~subliminal.subtitles.Subtitle`
    :return: the matching probability
    :rtype: float

    """
    guess = guessit.guess_file_info(subtitle.release, 'autodetect')
    video_keywords = get_keywords(video.guess)
    subtitle_keywords = get_keywords(guess) | subtitle.keywords
    replacement = {'keywords': len(video_keywords & subtitle_keywords)}
    if isinstance(video, Episode):
        replacement.update({'series': 0, 'season': 0, 'episode': 0})
        matching_format = '{series:b}{season:b}{episode:b}{keywords:03b}'
        best = matching_format.format(series=1, season=1, episode=1, keywords=len(video_keywords))
        if guess['type'] in ['episode', 'episodesubtitle']:
            if 'series' in guess and guess['series'].lower() == video.series.lower():
                replacement['series'] = 1
            if 'season' in guess and guess['season'] == video.season:
                replacement['season'] = 1
            if 'episodeNumber' in guess and guess['episodeNumber'] == video.episode:
                replacement['episode'] = 1
    elif isinstance(video, Movie):
        replacement.update({'title': 0, 'year': 0})
        matching_format = '{title:b}{year:b}{keywords:03b}'
        best = matching_format.format(title=1, year=1, keywords=len(video_keywords))
        if guess['type'] in ['movie', 'moviesubtitle']:
            if 'title' in guess and guess['title'].lower() == video.title.lower():
                replacement['title'] = 1
            if 'year' in guess and guess['year'] == video.year:
                replacement['year'] = 1
    else:
        return 0
    confidence = float(int(matching_format.format(**replacement), 2)) / float(int(best, 2))
    return confidence


def key_subtitles(subtitle, video, languages, services, order):
    """Create a key to sort subtitle using the given order

    :param subtitle: subtitle to sort
    :type subtitle: :class:`~subliminal.subtitles.ResultSubtitle`
    :param video: video to match
    :type video: :class:`~subliminal.videos.Video`
    :param list languages: languages in preferred order
    :param list services: services in preferred order
    :param order: preferred order for subtitles sorting
    :type list: list of :data:`LANGUAGE_INDEX`, :data:`SERVICE_INDEX`, :data:`SERVICE_CONFIDENCE`, :data:`MATCHING_CONFIDENCE`
    :return: a key ready to use for subtitles sorting
    :rtype: int

    """
    key = ''
    for sort_item in order:
        if sort_item == LANGUAGE_INDEX:
            key += '{0:03d}'.format(len(languages) - languages.index(subtitle.language) - 1)
        elif sort_item == SERVICE_INDEX:
            key += '{0:02d}'.format(len(services) - services.index(subtitle.service) - 1)
        elif sort_item == SERVICE_CONFIDENCE:
            key += '{0:04d}'.format(int(subtitle.confidence * 1000))
        elif sort_item == MATCHING_CONFIDENCE:
            confidence = 0
            if subtitle.release:
                confidence = matching_confidence(video, subtitle)
            key += '{0:04d}'.format(int(confidence * 1000))
    return int(key)


def group_by_video(list_results):
    """Group the results of :class:`ListTasks <subliminal.tasks.ListTask>` into a
    dictionary of :class:`~subliminal.videos.Video` => :class:`~subliminal.subtitles.Subtitle`

    :param list_results:
    :type list_results: list of result of :class:`~subliminal.tasks.ListTask`
    :return: subtitles grouped by videos
    :rtype: dict of :class:`~subliminal.videos.Video` => [:class:`~subliminal.subtitles.Subtitle`]

    """
    result = defaultdict(list)
    for video, subtitles in list_results:
        result[video] += subtitles
    return result
