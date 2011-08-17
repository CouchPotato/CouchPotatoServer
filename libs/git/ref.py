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
class Ref(object):
    def __init__(self, repo, name):
        super(Ref, self).__init__()
        self.repo = repo
        self.name = name
    def getHead(self):
        return self.repo._getCommitByRefName(self.name)
    def getNormalizedName(self):
        return self.name
    def getNewCommits(self, comparedTo, limit=""):
        returned = []
        command = "git cherry %s %s %s" % (self.repo._normalizeRefName(comparedTo),
                                           self.getNormalizedName(),
                                           self.repo._normalizeRefName(limit))
        for line in self.repo._getOutputAssertSuccess(command).splitlines():
            symbol, sha = line.split()
            if symbol == '-':
                #already has an equivalent commit
                continue
            returned.append(self.repo._getCommitByHash(sha.strip()))
        return returned
    def __eq__(self, ref):
        return (type(ref) is type(self) and ref.name == self.name)
    def __ne__(self, ref):
        return not (self == ref)
    def __repr__(self):
        return "<%s %s>" % (type(self).__name__, self.getNormalizedName())
    ################################## Containment #################################
    def getMergeBase(self, other):
        return self.repo.getMergeBase(self, other)
    __and__ = getMergeBase
    def contains(self, other):
        return self.getMergeBase(other) == other
    __contains__ = contains

