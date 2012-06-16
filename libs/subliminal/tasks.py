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
__all__ = ['Task', 'ListTask', 'DownloadTask', 'StopTask']


class Task(object):
    """Base class for tasks to use in subliminal"""
    pass


class ListTask(Task):
    """List task used by the worker to search for subtitles

    :param video: video to search subtitles for
    :type video: :class:`~subliminal.videos.Video`
    :param list languages: languages to search for
    :param string service: name of the service to use
    :param config: configuration for the service
    :type config: :class:`~subliminal.services.ServiceConfig`

    """
    def __init__(self, video, languages, service, config):
        super(ListTask, self).__init__()
        self.video = video
        self.service = service
        self.languages = languages
        self.config = config

    def __repr__(self):
        return 'ListTask(%r, %r, %s, %r)' % (self.video, self.languages, self.service, self.config)


class DownloadTask(Task):
    """Download task used by the worker to download subtitles

    :param video: video to download subtitles for
    :type video: :class:`~subliminal.videos.Video`
    :param subtitles: subtitles to download in order of preference
    :type subtitles: list of :class:`~subliminal.subtitles.Subtitle`

    """
    def __init__(self, video, subtitles):
        super(DownloadTask, self).__init__()
        self.video = video
        self.subtitles = subtitles

    def __repr__(self):
        return 'DownloadTask(%r, %r)' % (self.video, self.subtitles)


class StopTask(Task):
    """Stop task that will stop the worker"""
    pass
