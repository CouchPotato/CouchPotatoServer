# -*- coding: utf-8 -*-
#
# Subliminal - Subtitles, faster than your thoughts
# Copyright (c) 2011 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of Subliminal.
#
# Subliminal is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__all__ = ['PLUGINS', 'API_PLUGINS', 'IDLE', 'RUNNING', 'PAUSED', 'Subliminal', 'PluginWorker', 'matching_confidence',
           'LANGUAGE_INDEX', 'PLUGIN_INDEX', 'PLUGIN_CONFIDENCE', 'MATCHING_CONFIDENCE']


from collections import defaultdict
from exceptions import InvalidLanguageError, PluginError, BadStateError, \
    WrongTaskError, DownloadFailedError
from itertools import groupby
from languages import list_languages
from subliminal.utils import NullHandler
from tasks import Task, DownloadTask, ListTask, StopTask
import Queue
import guessit
import logging
import os
import plugins
import subtitles
import threading
import utils
import videos

# init logger
logger = logging.getLogger('subliminal')
logger.addHandler(NullHandler())

# const
PLUGINS = ['OpenSubtitles', 'BierDopje', 'TheSubDB', 'SubsWiki', 'Subtitulos']
API_PLUGINS = filter(lambda p: getattr(plugins, p).api_based, PLUGINS)
IDLE, RUNNING, PAUSED = range(3)
LANGUAGE_INDEX, PLUGIN_INDEX, PLUGIN_CONFIDENCE, MATCHING_CONFIDENCE = range(4)


class Subliminal(object):
    """Main Subliminal class"""

    def __init__(self, cache_dir=None, workers=None, multi=False, force=False,
                 max_depth=None, filemode=None, sort_order=None, plugins=None, languages=None):
        self.multi = multi
        self.sort_order = sort_order or [LANGUAGE_INDEX, PLUGIN_INDEX, PLUGIN_CONFIDENCE]
        self.force = force
        self.max_depth = max_depth or 3
        self.taskQueue = Queue.PriorityQueue()
        self.listResultQueue = Queue.Queue()
        self.downloadResultQueue = Queue.Queue()
        self.languages = languages or []
        self.plugins = plugins or API_PLUGINS
        self._workers = workers or 4
        self.filemode = filemode
        self.state = IDLE
        self.cache_dir = cache_dir
        try:
            if cache_dir and not os.path.isdir(cache_dir):
                os.makedirs(cache_dir)
                logger.debug(u'Creating cache directory: %r' % cache_dir)
        except:
            self.cache_dir = None
            logger.error(u'Failed to use the cache directory, continue without it')

    def __enter__(self):
        self.startWorkers()
        return self

    def __exit__(self, *args):
        self.stopWorkers(0)

    @property
    def workers(self):
        return self._workers

    @workers.setter
    def workers(self, value):
        if self.state == RUNNING:
            raise BadStateError(self.state, IDLE)
        self._workers = value

    @property
    def languages(self):
        """Getter for languages"""
        return self._languages

    @languages.setter
    def languages(self, languages):
        """Setter for languages"""
        logger.debug(u'Setting languages to %r' % languages)
        self._languages = []
        for l in languages:
            if l not in list_languages(1):
                raise InvalidLanguageError(l)
            if not l in self._languages:
                self._languages.append(l)

    @property
    def plugins(self):
        """Getter for plugins"""
        return self._plugins

    @plugins.setter
    def plugins(self, plugins):
        """Setter for plugins"""
        logger.debug(u'Setting plugins to %r' % plugins)
        self._plugins = []
        for p in plugins:
            if p not in PLUGINS:
                raise PluginError(p)
            if not p in self._plugins:
                self._plugins.append(p)

    def listSubtitles(self, entries, auto=False):
        """
        Search subtitles within the plugins and return all found subtitles in a list of Subtitle object.

        Attributes:
            entries -- filepath or folderpath of video file or a list of that
            auto    -- automaticaly manage workers (default to False)"""
        if auto:
            if self.state != IDLE:
                raise BadStateError(self.state, IDLE)
            self.startWorkers()
        if isinstance(entries, basestring):
            entries = [entries]
        config = utils.PluginConfig(self.multi, self.cache_dir, self.filemode)
        scan_result = []
        for e in entries:
            if not isinstance(e, unicode):
                logger.warning(u'Entry %r is not unicode' % e)
            scan_result.extend(videos.scan(e))
        task_count = 0
        for video, subtitles in scan_result:
            languages = set([s.language for s in subtitles if s.language])
            wanted_languages = set(self._languages)
            if not wanted_languages:
                wanted_languages = list_languages(1)
            if not self.force and self.multi:
                wanted_languages = set(wanted_languages) - languages
                if not wanted_languages:
                    logger.debug(u'No need to list multi subtitles %r for %r because %r subtitles detected' % (self._languages, video.path, languages))
                    continue
            if not self.force and not self.multi and None in [s.language for s in subtitles]:
                logger.debug(u'No need to list single subtitles %r for %r because one detected' % (self._languages, video.path))
                continue
            logger.debug(u'Listing subtitles %r for %r with %r' % (wanted_languages, video.path, self._plugins))
            for plugin_name in self._plugins:
                plugin = getattr(plugins, plugin_name)
                to_list_languages = wanted_languages & plugin.availableLanguages()
                if not to_list_languages:
                    logger.debug(u'Skipping %r: none of wanted languages %r available in %r for plugin %s' % (video.path, wanted_languages, plugin.availableLanguages(), plugin_name))
                    continue
                if not plugin.isValidVideo(video):
                    logger.debug(u'Skipping %r: video %r is not part of supported videos %r for plugin %s' % (video.path, video, plugin.videos, plugin_name))
                    continue
                self.taskQueue.put((5, ListTask(video, to_list_languages, plugin_name, config)))
                task_count += 1
        subtitles = []
        for _ in range(task_count):
            subtitles.extend(self.listResultQueue.get())
        if auto:
            self.stopWorkers()
        return subtitles

    def downloadSubtitles(self, entries, auto=False):
        """
        Download subtitles using the plugins preferences and languages. Also use internal algorithm to find
        the best match inside a plugin.

        Attributes:
            entries -- filepath or folderpath of video file or a list of that
            auto    -- automaticaly manage workers (default to False)"""
        if auto:
            if self.state != IDLE:
                raise BadStateError(self.state, IDLE)
            self.startWorkers()
        by_video = self.groupByVideo(self.listSubtitles(entries, False))
        # Define an order with LANGUAGE_INDEX first for multi sorting
        order = self.sort_order
        if self.multi:
            order.insert(0, LANGUAGE_INDEX)
        task_count = 0
        for video, subtitles in by_video.iteritems():
            ordered_subtitles = sorted(subtitles, key=lambda s: self.keySubtitles(s, video, order), reverse=True)
            if not self.multi:
                self.taskQueue.put((5, DownloadTask(video, list(ordered_subtitles))))
                task_count += 1
                continue
            for _, by_language in groupby(ordered_subtitles, lambda s: s.language):
                self.taskQueue.put((5, DownloadTask(video, list(by_language))))
                task_count += 1
        downloaded = []
        for _ in range(task_count):
            downloaded.extend(self.downloadResultQueue.get())
        if auto:
            self.stopWorkers()
        return downloaded

    def keySubtitles(self, subtitle, video, order):
        """Create a key to sort subtitle using preferences"""
        key = ''
        for sort_item in order:
            if sort_item == LANGUAGE_INDEX:
                key += '{:03d}'.format(len(self._languages) - self._languages.index(subtitle.language) - 1)
            elif sort_item == PLUGIN_INDEX:
                key += '{:02d}'.format(len(self._plugins) - self._plugins.index(subtitle.plugin) - 1)
            elif sort_item == PLUGIN_CONFIDENCE:
                key += '{:04d}'.format(int(subtitle.confidence * 1000))
            elif sort_item == MATCHING_CONFIDENCE:
                confidence = 0
                if subtitle.release:
                    confidence = matching_confidence(video, subtitle)
                key += '{:04d}'.format(int(confidence * 1000))
        return int(key)

    def groupByVideo(self, list_result):
        '''Because list outputs a list of tuples from different plugins, we need to put them back
        together under a single video key'''
        result = defaultdict(list)
        for video, subtitles in list_result:
            result[video] += subtitles
        return result

    def startWorkers(self):
        """Create a pool of workers and start them"""
        if self.state == RUNNING:
            raise BadStateError(self.state, IDLE)
        self.pool = []
        for _ in range(self._workers):
            worker = PluginWorker(self.taskQueue, self.listResultQueue, self.downloadResultQueue)
            worker.start()
            self.pool.append(worker)
            logger.debug(u'Worker %s added to the pool' % worker.name)
        self.state = RUNNING

    def stopWorkers(self, priority=10):
        """Stop workers using a lowest priority stop signal and wait for them to terminate properly"""
        for _ in range(self._workers):
            self.taskQueue.put((priority, StopTask()))
        for worker in self.pool:
            worker.join()
        self.state = IDLE
        if not self.taskQueue.empty():
            self.state = PAUSED

    def pauseWorkers(self):
        """Pause workers using a highest priority stop signal and wait for them to terminate properly"""
        self.stopWorkers(0)

    def addTask(self, task):
        """Add a task with default priority"""
        if not isinstance(task, Task) or isinstance(task, StopTask):
            raise WrongTaskError()
        self.taskQueue.put((5, task))


class PluginWorker(threading.Thread):
    """Threaded plugin worker"""
    def __init__(self, taskQueue, listResultQueue, downloadResultQueue):
        threading.Thread.__init__(self)
        self.taskQueue = taskQueue
        self.listResultQueue = listResultQueue
        self.downloadResultQueue = downloadResultQueue
        self.logger = logging.getLogger('subliminal.worker')
        self.plugins = {}

    def run(self):
        while True:
            task = self.taskQueue.get()[1]
            if isinstance(task, StopTask):
                self.logger.debug(u'Poison pill received in thread %s' % self.name)
                self.taskQueue.task_done()
                break
            result = []
            try:
                if isinstance(task, ListTask):
                    if task.plugin not in self.plugins:  # init the plugin
                        self.plugins[task.plugin] = getattr(plugins, task.plugin)()
                        self.plugins[task.plugin].init()
                    # Retrieve the plugin list subtitles and return [(video, [subtitle])]
                    plugin = self.plugins[task.plugin]
                    plugin.config = task.config
                    subtitles = plugin.list(task.video, task.languages)
                    result = [(task.video, subtitles)]
                elif isinstance(task, DownloadTask):
                    # Attempt to download one subtitle from the given list
                    for subtitle in task.subtitles:
                        if subtitle.plugin not in self.plugins:  # init the plugin
                            self.plugins[subtitle.plugin] = getattr(plugins, subtitle.plugin)()
                            self.plugins[subtitle.plugin].init()
                        plugin = self.plugins[subtitle.plugin]
                        try:
                            result = [plugin.download(subtitle)]
                            break
                        except DownloadFailedError:  # try the next one
                            self.logger.warning(u'Could not download subtitle %r, trying next' % subtitle)
                            continue
                    if not result:
                        self.logger.error(u'No subtitles could be downloaded for video %r' % task.video.path or task.video.release)
            except:
                self.logger.error(u'Exception raised in worker %s' % self.name, exc_info=True)
            finally:
                # Put the result in the correct queue
                if isinstance(task, ListTask):
                    self.listResultQueue.put(result)
                elif isinstance(task, DownloadTask):
                    self.downloadResultQueue.put(result)
                self.taskQueue.task_done()
        self.terminate()
        self.logger.debug(u'Thread %s terminated' % self.name)

    def terminate(self):
        """Terminate instanciated plugins"""
        for plugin_name, plugin in self.plugins.iteritems():
            try:
                plugin.terminate()
            except:
                self.logger.error(u'Exception raised when terminating plugin %s' % plugin_name, exc_info=True)


def matching_confidence(video, subtitle):
    '''Compute the confidence that the subtitle matches the video.
    Returns a float between 0 and 1. 1 being the perfect match.'''
    guess = guessit.guess_file_info(subtitle.release, 'autodetect')
    video_keywords = utils.get_keywords(video.guess)
    subtitle_keywords = utils.get_keywords(guess) | subtitle.keywords
    replacement = {'keywords': len(video_keywords & subtitle_keywords)}
    if isinstance(video, videos.Episode):
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
    elif isinstance(video, videos.Movie):
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
