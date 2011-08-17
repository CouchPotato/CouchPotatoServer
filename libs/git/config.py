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
from .exceptions import GitCommandFailedException

class GitConfiguration(object):
    def __init__(self, repo):
        super(GitConfiguration, self).__init__()
        self.repo = repo
    def setParameter(self, path, value, local=True):
        self.repo._executeGitCommandAssertSuccess("git config %s \"%s\" \"%s\"" % ("" if local else "--global", path, value))
    def unsetParameter(self, path, local=True):
        try:
            self.repo._executeGitCommandAssertSuccess("git config --unset %s \"%s\"" % ("" if local else "--global", path))
        except GitCommandFailedException:
            if self.getParameter(path) is not None:
                raise
    def getParameter(self, path):
        return self.getDict().get(path, None)
    def getDict(self):
        return dict(line.strip().split("=",1)
                    for line in self.repo._getOutputAssertSuccess("git config -l").splitlines())
