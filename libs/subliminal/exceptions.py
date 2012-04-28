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


class Error(Exception):
    """Base class for exceptions in subliminal"""
    pass


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


class InvalidServiceError(Error):
    """Exception raised when invalid service is submitted

    :param string service: service that causes the error

    """
    def __init__(self, service):
        self.service = service

    def __str__(self):
        return self.service


class ServiceError(Error):
    """"Exception raised by services"""
    pass


class WrongTaskError(Error):
    """"Exception raised when invalid task is submitted"""
    pass


class DownloadFailedError(Error):
    """"Exception raised when a download task has failed in service"""
    pass


class UnknownVideoError(Error):
    """"Exception raised when a video could not be identified"""
    pass
