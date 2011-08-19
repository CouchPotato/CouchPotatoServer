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
from .ref import Ref
from .files import ModifiedFile

SHA1_LENGTH = 40

class Commit(Ref):
    def __init__(self, repo, sha):
        sha = str(sha).lower()
        if len(sha) < SHA1_LENGTH:
            sha = repo._getCommitByPartialHash(sha).hash
        super(Commit, self).__init__(repo, sha)
        self.hash = sha
    def __repr__(self):
        return self.hash
    def __eq__(self, other):
        if not isinstance(other, Commit):
            if isinstance(other, Ref):
                other = other.getHead().hash
        else:
            other = other.hash
        if other is None:
            return False
        if not isinstance(other, basestring):
            raise TypeError("Comparing %s and %s" % (type(self), type(other)))
        return (self.hash == other.lower())
    def getParents(self):
        output = self.repo._getOutputAssertSuccess("git rev-list %s --parents -1" % self)
        return [Commit(self.repo, sha.strip()) for sha in output.split()[1:]]
    def getChange(self):
        returned = []
        for line in self.repo._getOutputAssertSuccess("git show --pretty=format: --raw %s" % self).splitlines():
            line = line.strip()
            if not line:
                continue
            filename = line.split()[-1]
            returned.append(ModifiedFile(filename))
        return returned
    getChangedFiles = getChange
    ############################ Misc. Commit attributes ###########################
    def _getCommitField(self, field):
        return self.repo._executeGitCommandAssertSuccess("git log -1 --pretty=format:%s %s" % (field, self)).stdout.read().strip()
    def getAuthorName(self):
        return self._getCommitField("%an")
    def getAuthorEmail(self):
        return self._getCommitField("%ae")
    def getDate(self):
        return int(self._getCommitField("%at"))
    def getSubject(self):
        return self._getCommitField("%s")
    def getMessageBody(self):
        return self._getCommitField("%b")
