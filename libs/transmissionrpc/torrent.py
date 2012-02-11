# -*- coding: utf-8 -*-
# Copyright (c) 2008-2011 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

import sys, datetime

from transmissionrpc.constants import PRIORITY
from transmissionrpc.utils import format_timedelta

class Torrent(object):
    """
    Torrent is a class holding the data received from Transmission regarding a bittorrent transfer.
    All fetched torrent fields are accessible through this class using attributes.
    This class has a few convenience properties using the torrent data.
    """

    def __init__(self, client, fields):
        if 'id' not in fields:
            raise ValueError('Torrent requires an id')
        self.fields = {}
        self.update(fields)
        self.client = client

    def _getNameString(self, codec=None):
        if codec is None:
            codec = sys.getdefaultencoding()
        name = None
        # try to find name
        if 'name' in self.fields:
            name = self.fields['name']
        # if name is unicode, try to decode
        if isinstance(name, unicode):
            try:
                name = name.encode(codec)
            except UnicodeError:
                name = None
        return name

    def __repr__(self):
        tid = self.fields['id']
        name = self._getNameString()
        if isinstance(name, str):
            return '<Torrent %d \"%s\">' % (tid, name)
        else:
            return '<Torrent %d>' % (tid)

    def __str__(self):
        name = self._getNameString()
        if isinstance(name, str):
            return 'Torrent \"%s\"' % (name)
        else:
            return 'Torrent'

    def __copy__(self):
        return Torrent(self.client, self.fields)

    def _rpc_version(self):
        if self.client:
            return self.client.rpc_version
        return 2
    
    def _status_old(self, code):
        mapping = {
            (1<<0): 'check pending',
            (1<<1): 'checking',
            (1<<2): 'downloading',
            (1<<3): 'seeding',
            (1<<4): 'stopped',
        }
        return mapping[code]
    
    def _status_new(self, code):
        mapping = {
            0: 'stopped',
            1: 'check pending',
            2: 'checking',
            3: 'download pending',
            4: 'downloading',
            5: 'seed pending',
            6: 'seeding',
        }
        return mapping[code]
    
    def _status(self):
        code = self.fields['status']
        if self._rpc_version() >= 14:
            return self._status_new(code)
        else:
            return self._status_old(code)

    def update(self, other):
        """
        Update the torrent data from a Transmission JSON-RPC arguments dictionary
        """
        fields = None
        if isinstance(other, dict):
            fields = other
        elif isinstance(other, Torrent):
            fields = other.fields
        else:
            raise ValueError('Cannot update with supplied data')
        for key, value in fields.iteritems():
            self.fields[key.replace('-', '_')] = value

    def files(self):
        """
        Get list of files for this torrent.

        This function returns a dictionary with file information for each file.
        The file information is has following fields:
        ::

            {
                <file id>: {
                    'name': <file name>,
                    'size': <file size in bytes>,
                    'completed': <bytes completed>,
                    'priority': <priority ('high'|'normal'|'low')>,
                    'selected': <selected for download>
                }
                ...
            }
        """
        result = {}
        if 'files' in self.fields:
            indices = xrange(len(self.fields['files']))
            files = self.fields['files']
            priorities = self.fields['priorities']
            wanted = self.fields['wanted']
            for item in zip(indices, files, priorities, wanted):
                selected = True if item[3] else False
                priority = PRIORITY[item[2]]
                result[item[0]] = {
                    'selected': selected,
                    'priority': priority,
                    'size': item[1]['length'],
                    'name': item[1]['name'],
                    'completed': item[1]['bytesCompleted']}
        return result

    def __getattr__(self, name):
        try:
            return self.fields[name]
        except KeyError:
            raise AttributeError('No attribute %s' % name)

    @property
    def status(self):
        """
        Returns the torrent status. Is either one of 'check pending', 'checking',
        'downloading', 'seeding' or 'stopped'. The first two is related to
        verification.
        """
        return self._status()

    @property
    def progress(self):
        """Get the download progress in percent."""
        try:
            return 100.0 * (self.fields['sizeWhenDone'] - self.fields['leftUntilDone']) / float(self.fields['sizeWhenDone'])
        except ZeroDivisionError:
            return 0.0

    @property
    def ratio(self):
        """Get the upload/download ratio."""
        return float(self.fields['uploadRatio'])

    @property
    def eta(self):
        """Get the "eta" as datetime.timedelta."""
        eta = self.fields['eta']
        if eta >= 0:
            return datetime.timedelta(seconds=eta)
        else:
            ValueError('eta not valid')

    @property
    def date_active(self):
        """Get the attribute "activityDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self.fields['activityDate'])

    @property
    def date_added(self):
        """Get the attribute "addedDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self.fields['addedDate'])

    @property
    def date_started(self):
        """Get the attribute "startDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self.fields['startDate'])

    @property
    def date_done(self):
        """Get the attribute "doneDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self.fields['doneDate'])

    def format_eta(self):
        """
        Returns the attribute *eta* formatted as a string.

        * If eta is -1 the result is 'not available'
        * If eta is -2 the result is 'unknown'
        * Otherwise eta is formatted as <days> <hours>:<minutes>:<seconds>.
        """
        eta = self.fields['eta']
        if eta == -1:
            return 'not available'
        elif eta == -2:
            return 'unknown'
        else:
            return format_timedelta(self.eta)

    @property
    def priority(self):
        """
        Get the priority as string.
        Can be one of 'low', 'normal', 'high'.
        """
        return PRIORITY[self.fields['bandwidthPriority']]