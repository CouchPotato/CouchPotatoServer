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
__all__ = ['Task', 'ListTask', 'DownloadTask', 'StopTask']


class Task(object):
    """Base class for tasks to use in subliminal"""
    pass


class ListTask(Task):
    """List task to list subtitles"""
    def __init__(self, video, languages, plugin, config):
        self.video = video
        self.plugin = plugin
        self.languages = languages
        self.config = config


class DownloadTask(Task):
    """Download task to download subtitles"""
    def __init__(self, video, subtitles):
        self.video = video
        self.subtitles = subtitles


class StopTask(Task):
    """Stop task to stop workers"""
    pass
