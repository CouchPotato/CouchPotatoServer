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
from .core import (consume_task, LANGUAGE_INDEX, SERVICE_INDEX,
    SERVICE_CONFIDENCE, MATCHING_CONFIDENCE, SERVICES, create_list_tasks,
    create_download_tasks, group_by_video, key_subtitles)
from .language import language_list, language_set, LANGUAGES
from .tasks import StopTask
import Queue
import logging
import threading


__all__ = ['Worker', 'Pool']
logger = logging.getLogger(__name__)


class Worker(threading.Thread):
    """Consume tasks and put the result in the queue"""
    def __init__(self, tasks, results):
        super(Worker, self).__init__()
        self.tasks = tasks
        self.results = results
        self.services = {}

    def run(self):
        while 1:
            result = []
            try:
                task = self.tasks.get(block=True)
                if isinstance(task, StopTask):
                    break
                result = consume_task(task, self.services)
                self.results.put((task.video, result))
            except:
                logger.error(u'Exception raised in worker %s' % self.name, exc_info=True)
            finally:
                self.tasks.task_done()
        self.terminate()
        logger.debug(u'Thread %s terminated' % self.name)

    def terminate(self):
        """Terminate instantiated services"""
        for service_name, service in self.services.iteritems():
            try:
                service.terminate()
            except:
                logger.error(u'Exception raised when terminating service %s' % service_name, exc_info=True)


class Pool(object):
    """Pool of workers"""
    def __init__(self, size):
        self.tasks = Queue.Queue()
        self.results = Queue.Queue()
        self.workers = []
        for _ in range(size):
            self.workers.append(Worker(self.tasks, self.results))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
        self.join()

    def start(self):
        """Start workers"""
        for worker in self.workers:
            worker.start()

    def stop(self):
        """Stop workers"""
        for _ in self.workers:
            self.tasks.put(StopTask())

    def join(self):
        """Join the task queue"""
        self.tasks.join()

    def collect(self):
        """Collect available results

        :return: results of tasks
        :rtype: list of :class:`~subliminal.tasks.Task`

        """
        results = []
        while 1:
            try:
                result = self.results.get(block=False)
                results.append(result)
            except Queue.Empty:
                break
        return results

    def list_subtitles(self, paths, languages=None, services=None, force=True, multi=False, cache_dir=None, max_depth=3, scan_filter=None):
        """See :meth:`subliminal.list_subtitles`"""
        services = services or SERVICES
        languages = language_set(languages) if languages is not None else language_set(LANGUAGES)
        if isinstance(paths, basestring):
            paths = [paths]
        if any([not isinstance(p, unicode) for p in paths]):
            logger.warning(u'Not all entries are unicode')
        tasks = create_list_tasks(paths, languages, services, force, multi, cache_dir, max_depth, scan_filter)
        for task in tasks:
            self.tasks.put(task)
        self.join()
        results = self.collect()
        return group_by_video(results)

    def download_subtitles(self, paths, languages=None, services=None, force=True, multi=False, cache_dir=None, max_depth=3, scan_filter=None, order=None):
        """See :meth:`subliminal.download_subtitles`"""
        services = services or SERVICES
        languages = language_list(languages) if languages is not None else language_list(LANGUAGES)
        if isinstance(paths, basestring):
            paths = [paths]
        order = order or [LANGUAGE_INDEX, SERVICE_INDEX, SERVICE_CONFIDENCE, MATCHING_CONFIDENCE]
        subtitles_by_video = self.list_subtitles(paths, languages, services, force, multi, cache_dir, max_depth, scan_filter)
        for video, subtitles in subtitles_by_video.iteritems():
            subtitles.sort(key=lambda s: key_subtitles(s, video, languages, services, order), reverse=True)
        tasks = create_download_tasks(subtitles_by_video, languages, multi)
        for task in tasks:
            self.tasks.put(task)
        self.join()
        results = self.collect()
        return group_by_video(results)
