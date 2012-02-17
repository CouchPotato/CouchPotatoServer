# -*- coding: utf-8 -*-
# Copyright (c) 2008-2011 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

import sys, datetime

from transmissionrpc.constants import PRIORITY, RATIO_LIMIT, IDLE_LIMIT
from transmissionrpc.utils import Field, format_timedelta

class Torrent(object):
    """
    Torrent is a class holding the data received from Transmission regarding a bittorrent transfer.
    All fetched torrent fields are accessible through this class using attributes.
    This class has a few convenience properties using the torrent data.
    """

    def __init__(self, client, fields):
        if 'id' not in fields:
            raise ValueError('Torrent requires an id')
        self._fields = {}
        self._update_fields(fields)
        self._incoming_pending= False
        self._outgoing_pending= False
        self._client = client

    def _getNameString(self, codec=None):
        if codec is None:
            codec = sys.getdefaultencoding()
        name = None
        # try to find name
        if 'name' in self._fields:
            name = self._fields['name'].value
        # if name is unicode, try to decode
        if isinstance(name, unicode):
            try:
                name = name.encode(codec)
            except UnicodeError:
                name = None
        return name

    def __repr__(self):
        tid = self._fields['id'].value
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
        return Torrent(self._client, self._fields)

    def __getattr__(self, name):
        try:
            return self._fields[name].value
        except KeyError:
            raise AttributeError('No attribute %s' % name)

    def _rpc_version(self):
        if self._client:
            return self._client.rpc_version
        return 2

    def _dirty_fields(self):
        """Enumerate changed fields"""
        outgoing_keys = ['bandwidthPriority', 'downloadLimit', 'downloadLimited', 'peer_limit', 'queuePosition'
            , 'seedIdleLimit', 'seedIdleMode', 'seedRatioLimit', 'seedRatioMode', 'uploadLimit', 'uploadLimited']
        fields = []
        for key in outgoing_keys:
            if key in self._fields and self._fields[key].dirty:
                fields.append(key)
        return fields

    def _push(self):
        """Push changed fields to the server"""
        dirty = self._dirty_fields()
        args = {}
        for key in dirty:
            args[key] = self._fields[key].value
            self._fields[key] = self._fields[key]._replace(dirty=False)
        if len(args) > 0:
            self._client.change_torrent(self.id, **args)

    def _update_fields(self, other):
        """
        Update the torrent data from a Transmission JSON-RPC arguments dictionary
        """
        fields = None
        if isinstance(other, dict):
            for key, value in other.iteritems():
                self._fields[key.replace('-', '_')] = Field(value, False)
        elif isinstance(other, Torrent):
            for key in other._fields.keys():
                self._fields[key] = Field(other._fields[key].value, False)
        else:
            raise ValueError('Cannot update with supplied data')
        self._incoming_pending = False
    
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
        code = self._fields['status'].value
        if self._rpc_version() >= 14:
            return self._status_new(code)
        else:
            return self._status_old(code)

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
        if 'files' in self._fields:
            files = self._fields['files'].value
            indices = xrange(len(files))
            priorities = self._fields['priorities'].value
            wanted = self._fields['wanted'].value
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
            size = self._fields['sizeWhenDone'].value
            left = self._fields['leftUntilDone'].value
            return 100.0 * (size - left) / float(size)
        except ZeroDivisionError:
            return 0.0

    @property
    def ratio(self):
        """Get the upload/download ratio."""
        return float(self._fields['uploadRatio'].value)

    @property
    def eta(self):
        """Get the "eta" as datetime.timedelta."""
        eta = self._fields['eta'].value
        if eta >= 0:
            return datetime.timedelta(seconds=eta)
        else:
            ValueError('eta not valid')

    @property
    def date_active(self):
        """Get the attribute "activityDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self._fields['activityDate'].value)

    @property
    def date_added(self):
        """Get the attribute "addedDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self._fields['addedDate'].value)

    @property
    def date_started(self):
        """Get the attribute "startDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self._fields['startDate'].value)

    @property
    def date_done(self):
        """Get the attribute "doneDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self._fields['doneDate'].value)

    def format_eta(self):
        """
        Returns the attribute *eta* formatted as a string.

        * If eta is -1 the result is 'not available'
        * If eta is -2 the result is 'unknown'
        * Otherwise eta is formatted as <days> <hours>:<minutes>:<seconds>.
        """
        eta = self._fields['eta'].value
        if eta == -1:
            return 'not available'
        elif eta == -2:
            return 'unknown'
        else:
            return format_timedelta(self.eta)

    def _get_download_limit(self):
        """
        Get the download limit.
        Can be a number or None.
        """
        if self._fields['downloadLimited'].value:
            return self._fields['downloadLimit'].value
        else:
            return None

    def _set_download_limit(self, limit):
        """
        Get the download limit.
        Can be a number, 'session' or None.
        """
        if isinstance(limit, (int, long)):
            self._fields['downloadLimited'] = Field(True, True)
            self._fields['downloadLimit'] = Field(limit, True)
            self._push()
        elif limit == None:
            self._fields['downloadLimited'] = Field(False, True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    download_limit = property(_get_download_limit, _set_download_limit, None, "Download limit in Kbps or None. This is a mutator.")

    def _get_peer_limit(self):
        """
        Get the peer limit.
        """
        return self._fields['peer_limit'].value

    def _set_peer_limit(self, limit):
        """
        Set the peer limit.
        """
        if isinstance(limit, (int, long)):
            self._fields['peer_limit'] = Field(limit, True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    peer_limit = property(_get_peer_limit, _set_peer_limit, None, "Peer limit. This is a mutator.")

    def _get_priority(self):
        """
        Get the priority as string.
        Can be one of 'low', 'normal', 'high'.
        """
        return PRIORITY[self._fields['bandwidthPriority'].value]

    def _set_priority(self, priority):
        """
        Set the priority as string.
        Can be one of 'low', 'normal', 'high'.
        """
        if isinstance(priority, (str, unicode)):
            self._fields['bandwidthPriority'] = Field(PRIORITY[priority], True)
            self._push()

    priority = property(_get_priority, _set_priority, None
        , "Bandwidth priority as string. Can be one of 'low', 'normal', 'high'. This is a mutator.")

    def _get_seed_idle_limit(self):
        """
        Get the seed idle limit in minutes.
        """
        return self._fields['seedIdleLimit'].value

    def _set_seed_idle_limit(self, limit):
        """
        Set the seed idle limit in minutes.
        """
        if isinstance(limit, (int, long)):
            self._fields['seedIdleLimit'] = Field(limit, True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    seed_idle_limit = property(_get_seed_idle_limit, _set_seed_idle_limit, None
        , "Torrent seed idle limit in minutes. Also see seed_idle_mode. This is a mutator.")

    def _get_seed_idle_mode(self):
        """
        Get the seed ratio mode as string. Can be one of 'global', 'single' or 'unlimited'.
        """
        return IDLE_LIMIT[self._fields['seedIdleMode'].value]

    def _set_seed_idle_mode(self, mode):
        """
        Set the seed ratio mode as string. Can be one of 'global', 'single' or 'unlimited'.
        """
        if isinstance(mode, str):
            self._fields['seedIdleMode'] = Field(IDLE_LIMIT[mode], True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    seed_idle_mode = property(_get_seed_idle_mode, _set_seed_idle_mode, None,
        """
        Seed idle mode as string. Can be one of 'global', 'single' or 'unlimited'.

         * global, use session seed idle limit.
         * single, use torrent seed idle limit. See seed_idle_limit.
         * unlimited, no seed idle limit.

        This is a mutator.
        """
    )

    def _get_seed_ratio_limit(self):
        """
        Get the seed ratio limit as float.
        """
        return float(self._fields['seedRatioLimit'].value)

    def _set_seed_ratio_limit(self, limit):
        """
        Set the seed ratio limit as float.
        """
        if isinstance(limit, (int, long, float)) and limit >= 0.0:
            self._fields['seedRatioLimit'] = Field(float(limit), True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    seed_ratio_limit = property(_get_seed_ratio_limit, _set_seed_ratio_limit, None
        , "Torrent seed ratio limit as float. Also see seed_ratio_mode. This is a mutator.")

    def _get_seed_ratio_mode(self):
        """
        Get the seed ratio mode as string. Can be one of 'global', 'single' or 'unlimited'.
        """
        return RATIO_LIMIT[self._fields['seedRatioMode'].value]

    def _set_seed_ratio_mode(self, mode):
        """
        Set the seed ratio mode as string. Can be one of 'global', 'single' or 'unlimited'.
        """
        if isinstance(mode, str):
            self._fields['seedRatioMode'] = Field(RATIO_LIMIT[mode], True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    seed_ratio_mode = property(_get_seed_ratio_mode, _set_seed_ratio_mode, None,
        """
        Seed ratio mode as string. Can be one of 'global', 'single' or 'unlimited'.

         * global, use session seed ratio limit.
         * single, use torrent seed ratio limit. See seed_ratio_limit.
         * unlimited, no seed ratio limit.

        This is a mutator.
        """
    )

    def _get_upload_limit(self):
        """
        Get the upload limit.
        Can be a number or None.
        """
        if self._fields['uploadLimited'].value:
            return self._fields['uploadLimit'].value
        else:
            return None

    def _set_upload_limit(self, limit):
        """
        Set the upload limit.
        Can be a number, 'session' or None.
        """
        if isinstance(limit, (int, long)):
            self._fields['uploadLimited'] = Field(True, True)
            self._fields['uploadLimit'] = Field(limit, True)
            self._push()
        elif limit == None:
            self._fields['uploadLimited'] = Field(False, True)
            self._push()
        else:
            raise ValueError("Not a valid limit")

    upload_limit = property(_get_upload_limit, _set_upload_limit, None, "Upload limit in Kbps or None. This is a mutator.")

    def _get_queue_position(self):
        if self._rpc_version() >= 14:
            return self._fields['queuePosition'].value
        else:
            return 0

    def _set_queue_position(self, position):
        if self._rpc_version() >= 14:
            if isinstance(position, (int, long)):
                self._fields['queuePosition'] = Field(position, True)
                self._push()
            else:
                raise ValueError("Not a valid position")
        else:
            pass

    queue_position = property(_get_queue_position, _set_queue_position, None, "Queue position")

    def update(self, timeout=None):
        """Update the torrent information."""
        self._push()
        torrent = self._client.get_torrent(self.id, timeout=timeout)
        self._update_fields(torrent)

    def start(self, bypass_queue=False, timeout=None):
        """
        Start the torrent.
        """
        self._incoming_pending = True
        self._client.start_torrent(self.id, bypass_queue=bypass_queue, timeout=timeout)

    def stop(self, timeout=None):
        """Stop the torrent."""
        self._incoming_pending = True
        self._client.stop_torrent(self.id, timeout=timeout)

    def move_data(self, location, timeout=None):
        """Move torrent data to location."""
        self._incoming_pending = True
        self._client.move_torrent_data(self.id, location, timeout=timeout)

    def locate_data(self, location, timeout=None):
        """Locate torrent data at location."""
        self._incoming_pending = True
        self._client.locate_torrent_data(self.id, location, timeout=timeout)
