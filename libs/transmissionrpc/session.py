# -*- coding: utf-8 -*-
# Copyright (c) 2008-2011 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

class Session(object):
    """
    Session is a class holding the session data for a Transmission daemon.

    Access the session field can be done through attributes.
    The attributes available are the same as the session arguments in the
    Transmission RPC specification, but with underscore instead of hyphen.
    ``download-dir`` -> ``download_dir``.
    """

    def __init__(self, fields=None):
        self.fields = {}
        if fields is not None:
            self.update(fields)

    def update(self, other):
        """Update the session data from a session arguments dictionary"""

        fields = None
        if isinstance(other, dict):
            fields = other
        elif isinstance(other, Session):
            fields = other.fields
        else:
            raise ValueError('Cannot update with supplied data')

        for key, value in fields.iteritems():
            self.fields[key.replace('-', '_')] = value

    def __getattr__(self, name):
        try:
            return self.fields[name]
        except KeyError:
            raise AttributeError('No attribute %s' % name)

    def __str__(self):
        text = ''
        for key in sorted(self.fields.keys()):
            text += "% 32s: %s\n" % (key[-32:], self.fields[key])
        return text
