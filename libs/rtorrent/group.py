# Copyright (c) 2013 Dean Gardiner, <gardiner91@gmail.com>
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import rtorrent.rpc

Method = rtorrent.rpc.Method


class Group:
    __name__ = 'Group'

    def __init__(self, _rt_obj, name):
        self._rt_obj = _rt_obj
        self.name = name

        self.methods = [
            # RETRIEVERS
            Method(Group, 'get_max', 'group.' + self.name + '.ratio.max', varname='max'),
            Method(Group, 'get_min', 'group.' + self.name + '.ratio.min', varname='min'),
            Method(Group, 'get_upload', 'group.' + self.name + '.ratio.upload', varname='upload'),

            # MODIFIERS
            Method(Group, 'set_max', 'group.' + self.name + '.ratio.max.set', varname='max'),
            Method(Group, 'set_min', 'group.' + self.name + '.ratio.min.set', varname='min'),
            Method(Group, 'set_upload', 'group.' + self.name + '.ratio.upload.set', varname='upload')
        ]

        rtorrent.rpc._build_rpc_methods(self, self.methods)

        # Setup multicall_add method
        caller = lambda multicall, method, *args: \
            multicall.add(method, *args)
        setattr(self, "multicall_add", caller)

    def _get_prefix(self):
        return 'group.' + self.name + '.ratio.'

    def update(self):
        multicall = rtorrent.rpc.Multicall(self)

        retriever_methods = [m for m in self.methods
                             if m.is_retriever() and m.is_available(self._rt_obj)]

        for method in retriever_methods:
            multicall.add(method)

        multicall.call()

    def enable(self):
        p = self._rt_obj._get_conn()
        return getattr(p, self._get_prefix() + 'enable')()

    def disable(self):
        p = self._rt_obj._get_conn()
        return getattr(p, self._get_prefix() + 'disable')()

    def set_command(self, *methods):
        methods = [m + '=' for m in methods]

        m = rtorrent.rpc.Multicall(self)
        self.multicall_add(
            m, 'system.method.set',
            self._get_prefix() + 'command',
            *methods
        )

        return(m.call()[-1])
