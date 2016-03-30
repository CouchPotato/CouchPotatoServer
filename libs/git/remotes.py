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
from . import branch
from . import ref_container

class Remote(ref_container.RefContainer):
    def __init__(self, repo, name, url):
        super(Remote, self).__init__()
        self.repo = repo
        self.name = name
        self.url = url
    def fetch(self):
        self.repo._executeGitCommandAssertSuccess("fetch %s" % self.name)
    def prune(self):
        self.repo._executeGitCommandAssertSuccess("remote prune %s" % self.name)
    def __eq__(self, other):
        return (type(self) is type(other)) and (self.name == other.name)
    ###################### For compatibility with RefContainer #####################
    def getBranches(self):
        prefix = "%s/" % self.name
        returned = []
        for line in self.repo._getOutputAssertSuccess("branch -r").splitlines():
            if self.repo.getGitVersion() >= '1.6.3' and ' -> ' in line:
                continue
            line = line.strip()
            if line.startswith(prefix):
                returned.append(branch.RegisteredRemoteBranch(self.repo, self, line[len(prefix):]))
        return returned

