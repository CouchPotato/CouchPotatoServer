# Copyright (c) 2009, Rotem Yaari <vmalloc@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of organization nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY Rotem Yaari ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Rotem Yaari BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import os

class GitException(Exception):
    def __init__(self, msg):
        super(GitException, self).__init__()
        self.msg = msg
    def __repr__(self):
        return "%s: %s" % (type(self).__name__, self.msg)
    __str__ = __repr__

class CannotFindRepository(GitException):
    pass

class MergeConflict(GitException):
    def __init__(self, msg='Merge Conflict'):
        super(MergeConflict, self).__init__(msg=msg)

class GitCommandFailedException(GitException):
    def __init__(self, directory, command, popen):
        super(GitCommandFailedException, self).__init__(None)
        self.command = command
        self.directory = os.path.abspath(directory)
        self.stderr = popen.stderr.read()
        self.stdout = popen.stdout.read()
        self.popen = popen
        self.msg = "Command %r failed in %s (%s):\n%s\n%s" % (command, self.directory, popen.returncode,
                              self.stderr, self.stdout)
class NonexistentRefException(GitException):
    pass
