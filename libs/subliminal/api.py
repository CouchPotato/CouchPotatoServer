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
from .core import (SERVICES, LANGUAGE_INDEX, SERVICE_INDEX, SERVICE_CONFIDENCE,
    MATCHING_CONFIDENCE, create_list_tasks, consume_task, create_download_tasks,
    group_by_video, key_subtitles)
from .languages import list_languages
import logging


__all__ = ['list_subtitles', 'download_subtitles']
logger = logging.getLogger(__name__)


def list_subtitles(paths, languages=None, services=None, force=True, multi=False, cache_dir=None, max_depth=3):
    """List subtitles in given paths according to the criteria

    :param paths: path(s) to video file or folder
    :type paths: string or list
    :param list languages: languages to search for, in preferred order
    :param list services: services to use for the search, in preferred order
    :param bool force: force searching for subtitles even if some are detected
    :param bool multi: search multiple languages for the same video
    :param string cache_dir: path to the cache directory to use
    :param int max_depth: maximum depth for scanning entries
    :return: found subtitles
    :rtype: dict of :class:`~subliminal.videos.Video` => [:class:`~subliminal.subtitles.ResultSubtitle`]

    """
    services = services or SERVICES
    languages = set(languages or list_languages(1))
    if isinstance(paths, basestring):
        paths = [paths]
    if any([not isinstance(p, unicode) for p in paths]):
        logger.warning(u'Not all entries are unicode')
    results = []
    service_instances = {}
    tasks = create_list_tasks(paths, languages, services, force, multi, cache_dir, max_depth)
    for task in tasks:
        try:
            result = consume_task(task, service_instances)
            results.append((task.video, result))
        except:
            logger.error(u'Error consuming task %r' % task, exc_info=True)
    for service_instance in service_instances.itervalues():
        service_instance.terminate()
    return group_by_video(results)


def download_subtitles(paths, languages=None, services=None, force=True, multi=False, cache_dir=None, max_depth=3, order=None):
    """Download subtitles in given paths according to the criteria

    :param paths: path(s) to video file or folder
    :type paths: string or list
    :param list languages: languages to search for, in preferred order
    :param list services: services to use for the search, in preferred order
    :param bool force: force searching for subtitles even if some are detected
    :param bool multi: search multiple languages for the same video
    :param string cache_dir: path to the cache directory to use
    :param int max_depth: maximum depth for scanning entries
    :param order: preferred order for subtitles sorting
    :type list: list of :data:`~subliminal.core.LANGUAGE_INDEX`, :data:`~subliminal.core.SERVICE_INDEX`, :data:`~subliminal.core.SERVICE_CONFIDENCE`, :data:`~subliminal.core.MATCHING_CONFIDENCE`
    :return: found subtitles
    :rtype: list of (:class:`~subliminal.videos.Video`, [:class:`~subliminal.subtitles.ResultSubtitle`])

    """
    services = services or SERVICES
    languages = languages or list_languages(1)
    if isinstance(paths, basestring):
        paths = [paths]
    order = order or [LANGUAGE_INDEX, SERVICE_INDEX, SERVICE_CONFIDENCE, MATCHING_CONFIDENCE]
    subtitles_by_video = list_subtitles(paths, set(languages), services, force, multi, cache_dir, max_depth)
    for video, subtitles in subtitles_by_video.iteritems():
        subtitles.sort(key=lambda s: key_subtitles(s, video, languages, services, order), reverse=True)
    results = []
    service_instances = {}
    tasks = create_download_tasks(subtitles_by_video, multi)
    for task in tasks:
        try:
            result = consume_task(task, service_instances)
            results.append(result)
        except:
            logger.error(u'Error consuming task %r' % task, exc_info=True)
    for service_instance in service_instances.itervalues():
        service_instance.terminate()
    return results
