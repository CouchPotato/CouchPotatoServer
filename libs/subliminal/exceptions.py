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


class Error(Exception):
    """Base class for exceptions in subliminal"""
    pass


class BadStateError(Error):
    """Exception raised when an invalid action is asked

    Attributes:
        current  -- current state of Subliminal instance
        expected -- expected state of Subliminal instance
    """
    def __init__(self, current, expected):
        self.current = current
        self.expected = expected

    def __str__(self):
        return 'Expected state %d but current state is %d' % (self.expected, self.current)


class InvalidLanguageError(Error):
    """Exception raised when invalid language is submitted

    Attributes:
        language -- language that cause the error
    """
    def __init__(self, language):
        self.language = language

    def __str__(self):
        return self.language


class MissingLanguageError(Error):
    """Exception raised when a missing language is found

    Attributes:
        language -- the missing language
    """
    def __init__(self, language):
        self.language = language

    def __str__(self):
        return self.language


class InvalidPluginError(Error):
    """"Exception raised when invalid plugin is submitted

    Attributes:
        plugin -- plugin that cause the error
    """
    def __init__(self, plugin):
        self.plugin = plugin

    def __str__(self):
        return self.plugin


class PluginError(Error):
    """"Exception raised by plugins"""
    pass


class WrongTaskError(Error):
    """"Exception raised when invalid task is submitted"""
    pass


class DownloadFailedError(Error):
    """"Exception raised when a download task has failed in plugin"""
    pass


class UnknownVideoError(Error):
    """"Exception raised when a video could not be identified"""
    pass
