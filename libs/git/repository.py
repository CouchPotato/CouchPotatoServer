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
import re
import os
import subprocess
import sys

from . import branch
from . import commit
from . import config
from .files import ModifiedFile
from . import ref
from . import ref_container
from . import remotes
from .utils import quote_for_shell
from .utils import CommandString as CMD

#exceptions
from .exceptions import CannotFindRepository
from .exceptions import GitException
from .exceptions import GitCommandFailedException
from .exceptions import MergeConflict

BRANCH_ALIAS_MARKER = ' -> '

class Repository(ref_container.RefContainer):
    ############################# internal methods #############################
    _loggingEnabled = False
    def _getWorkingDirectory(self):
        return '.'
    def _logGitCommand(self, command, cwd):
        if self._loggingEnabled:
            print >> sys.stderr, ">>", command
    def enableLogging(self):
        self._loggingEnabled = True
    def disableLogging(self):
        self._loggingEnabled = False
    def _executeGitCommand(self, command, cwd=None):
        if cwd is None:
            cwd = self._getWorkingDirectory()
        command = str(command)
        self._logGitCommand(command, cwd)
        returned = subprocess.Popen(command,
                                    shell=True,
                                    cwd=cwd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        returned.wait()
        return returned
    def _executeGitCommandAssertSuccess(self, command, **kwargs):
        returned = self._executeGitCommand(command, **kwargs)
        assert returned.returncode is not None
        if returned.returncode != 0:
            raise GitCommandFailedException(kwargs.get('cwd', self._getWorkingDirectory()), command, returned)
        return returned
    def _getOutputAssertSuccess(self, command, **kwargs):
        return self._executeGitCommandAssertSuccess(command, **kwargs).stdout.read()
    def _getMergeBase(self, a, b):
        raise NotImplementedError()
    def getMergeBase(self, a, b):
        repo = self
        if isinstance(b, commit.Commit) and isinstance(b.repo, LocalRepository):
            repo = b.repo
        elif isinstance(a, commit.Commit) and isinstance(a.repo, LocalRepository):
            repo = a.repo
        return repo._getMergeBase(a, b)


############################## remote repositories #############################
class RemoteRepository(Repository):
    def __init__(self, url):
        super(RemoteRepository, self).__init__()
        self.url = url
    def _getRefs(self, prefix):
        output = self._executeGitCommandAssertSuccess("git ls-remote %s" % (self.url,))
        for output_line in output.stdout:
            commit, refname = output_line.split()
            if refname.startswith(prefix):
                yield refname[len(prefix):]
    def _getRefsAsClass(self, prefix, cls):
        return [cls(self, ref) for ref in self._getRefs(prefix)]
    def getBranches(self):
        return self._getRefsAsClass('refs/heads/', branch.RemoteBranch)
############################## local repositories ##############################
class LocalRepository(Repository):
    def __init__(self, path):
        super(LocalRepository, self).__init__()
        self.path = path
        self.config = config.GitConfiguration(self)
        self._version = None
    def __repr__(self):
        return "<Git Repository at %s>" % (self.path,)
    def _getWorkingDirectory(self):
        return self.path
    def _getCommitByHash(self, sha):
        return commit.Commit(self, sha)
    def _getCommitByRefName(self, name):
        return commit.Commit(self, self._getOutputAssertSuccess("git rev-parse %s" % name).strip())
    def _getCommitByPartialHash(self, sha):
        return self._getCommitByRefName(sha)
    def getGitVersion(self):
        if self._version is None:
            version_output = self._getOutputAssertSuccess("git version")
            version_match = re.match(r"git\s+version\s+(\S+)$", version_output, re.I)
            if version_match is None:
                raise GitException("Cannot extract git version (unfamiliar output format %r?)" % version_output)
            self._version = version_match.group(1)
        return self._version
    ########################### Initializing a repository ##########################
    def init(self, bare=False):
        if not os.path.exists(self.path):
            os.mkdir(self.path)
        if not os.path.isdir(self.path):
            raise GitException("Cannot create repository in %s - "
                               "not a directory" % self.path)
        self._executeGitCommandAssertSuccess("git init %s" % ("--bare" if bare else ""))
    def _asURL(self, repo):
        if isinstance(repo, LocalRepository):
            repo = repo.path
        elif isinstance(repo, RemoteRepository):
            repo = repo.url
        elif not isinstance(repo, basestring):
            raise TypeError("Cannot clone from %r" % (repo,))
        return repo
    def clone(self, repo):
        self._executeGitCommandAssertSuccess("git clone %s %s" % (self._asURL(repo), self.path), cwd=".")
    ########################### Querying repository refs ###########################
    def getBranches(self):
        returned = []
        for git_branch_line in self._executeGitCommandAssertSuccess("git branch").stdout:
            if git_branch_line.startswith("*"):
                git_branch_line = git_branch_line[1:]
            git_branch_line = git_branch_line.strip()
            if BRANCH_ALIAS_MARKER in git_branch_line:
                alias_name, aliased = git_branch_line.split(BRANCH_ALIAS_MARKER)
                returned.append(branch.LocalBranchAlias(self, alias_name, aliased))
            else:
                returned.append(branch.LocalBranch(self, git_branch_line))
        return returned
    def _getCommits(self, specs, includeMerges):
        command = "git log --pretty=format:%%H %s" % specs
        if not includeMerges:
            command += " --no-merges"
        for c in self._executeGitCommandAssertSuccess(command).stdout:
            yield commit.Commit(self, c.strip())
    def getCommits(self, start=None, end="HEAD", includeMerges=True):
        spec = self._normalizeRefName(start or "")
        spec += ".."
        spec += self._normalizeRefName(end)
        return list(self._getCommits(spec, includeMerges=includeMerges))
    def getCurrentBranch(self):
        #todo: improve this method of obtaining current branch
        for branch_name in self._executeGitCommandAssertSuccess("git branch").stdout:
            branch_name = branch_name.strip()
            if not branch_name.startswith("*"):
                continue
            branch_name = branch_name[1:].strip()
            if branch_name == '(no branch)':
                return None
            return self.getBranchByName(branch_name)
    def getRemotes(self):
        config_dict = self.config.getDict()
        returned = []
        for line in self._getOutputAssertSuccess("git remote show -n").splitlines():
            line = line.strip()
            returned.append(remotes.Remote(self, line, config_dict.get('remote.%s.url' % line.strip())))
        return returned
    def getRemoteByName(self, name):
        return self._getByName(self.getRemotes, name)
    def _getMergeBase(self, a, b):
        if isinstance(a, ref.Ref):
            a = a.getHead()
        if isinstance(b, ref.Ref):
            b = b.getHead()
        returned = self._executeGitCommand("git merge-base %s %s" % (a, b))
        if returned.returncode == 0:
            return commit.Commit(self, returned.stdout.read().strip())
        # make sure this is not a misc. error with git 
        unused = self.getHead()
        return None
    ################################ Querying Status ###############################
    def containsCommit(self, commit):
        try:
            self._executeGitCommandAssertSuccess("git log -1 %s" % (commit,))
        except GitException:
            return False
        return True
    def getHead(self):
        return self._getCommitByRefName("HEAD")
    def _getFiles(self, *flags):
        flags = ["--exclude-standard"] + list(flags)
        return [f.strip()
                for f in self._getOutputAssertSuccess("git ls-files %s" % (" ".join(flags))).splitlines()]
    def _getRawDiff(self, *flags):
        flags = " ".join(str(f) for f in flags)
        return [ModifiedFile(line.split()[-1]) for line in
                self._getOutputAssertSuccess("git diff --raw %s" % flags).splitlines()]
    def getStagedFiles(self):
        if self.isInitialized():
            return self._getRawDiff('--cached')
        return self._getFiles()
    def getUnchangedFiles(self):
        return self._getFiles()
    def getChangedFiles(self):
        return self._getRawDiff()
    def getUntrackedFiles(self):
        return self._getFiles("--others")
    def isInitialized(self):
        try:
            self.getHead()
            return True
        except GitException:
            return False
    def isValid(self):
        return os.path.isdir(os.path.join(self.path, ".git")) or \
               (os.path.isfile(os.path.join(self.path, "HEAD")) and os.path.isdir(os.path.join(self.path, "objects")))
    def isWorkingDirectoryClean(self):
        return not (self.getUntrackedFiles() or self.getChangedFiles() or self.getStagedFiles())
    def __contains__(self, thing):
        if isinstance(thing, basestring) or isinstance(thing, commit.Commit):
            return self.containsCommit(thing)
        raise NotImplementedError()
    ################################ Staging content ###############################
    def add(self, path):
        self._executeGitCommandAssertSuccess("git add %s" % quote_for_shell(path))
    def addAll(self):
        return self.add('.')
    ################################## Committing ##################################
    def _normalizeRefName(self, thing):
        if isinstance(thing, ref.Ref):
            thing = thing.getNormalizedName()
        return str(thing)
    def _deduceNewCommitFromCommitOutput(self, output):
        for pattern in [
            # new-style commit pattern
            r"^\[\S+\s+(?:\(root-commit\)\s+)?(\S+)\]",
                        ]:
            match = re.search(pattern, output)
            if match:
                return commit.Commit(self, match.group(1))
        return None
    def commit(self, message, allowEmpty=False):
        command = "git commit -m %s" % quote_for_shell(message)
        if allowEmpty:
            command += " --allow-empty"
        output = self._getOutputAssertSuccess(command)
        return self._deduceNewCommitFromCommitOutput(output)
    ################################ Changing state ################################
    def createBranch(self, name, startingPoint=None):
        command = "git branch %s " % name
        if startingPoint is not None:
            command += self._normalizeRefName(startingPoint)
        self._executeGitCommandAssertSuccess(command)
        return branch.LocalBranch(self, name)
    def checkout(self, thing=None, targetBranch=None, files=()):
        if thing is None:
            thing = ""
        command = "git checkout %s" % (self._normalizeRefName(thing),)
        if targetBranch is not None:
            command += " -b %s" % (targetBranch,)
        if files:
            command += " -- %s" % " ".join(files)
        self._executeGitCommandAssertSuccess(command)
    def mergeMultiple(self, srcs, allowFastForward=True, log=False, message=None):
        try:
            self._executeGitCommandAssertSuccess(CMD("git merge",
                                                     " ".join(self._normalizeRefName(src) for src in srcs),
                                                     "--no-ff" if not allowFastForward else None,
                                                     "--log" if log else None,
                                                     ("-m \"%s\"" % message) if message is not None else None))
        except GitCommandFailedException, e:
            # git-merge tends to ignore the stderr rule...
            output = e.stdout + e.stderr
            if 'conflict' in output.lower():
                raise MergeConflict()
            raise
    def merge(self, src, *args, **kwargs):
        return self.mergeMultiple([src], *args, **kwargs)
    def _reset(self, flag, thing):
        command = "git reset %s %s" % (
            flag,
            self._normalizeRefName(thing))
        self._executeGitCommandAssertSuccess(command)
    def resetSoft(self, thing="HEAD"):
        return self._reset("--soft", thing)
    def resetHard(self, thing="HEAD"):
        return self._reset("--hard", thing)
    def resetMixed(self, thing="HEAD"):
        return self._reset("--mixed", thing)
    def _clean(self, flags):
        self._executeGitCommandAssertSuccess("git clean -q " + flags)
    def cleanIgnoredFiles(self):
        """Cleans files that match the patterns in .gitignore"""
        return self._clean("-f -X")
    def cleanUntrackedFiles(self):
        return self._clean("-f -d")
    ################################# collaboration ################################
    def addRemote(self, name, url):
        self._executeGitCommandAssertSuccess("git remote add %s %s" % (name, url))
        return remotes.Remote(self, name, url)
    def fetch(self, repo=None):
        command = "git fetch"
        if repo is not None:
            command += " "
            command += self._asURL(repo)
        self._executeGitCommandAssertSuccess(command)
    def pull(self, repo=None):
        command = "git pull"
        if repo is not None:
            command += " "
            command += self._asURL(repo)
        self._executeGitCommandAssertSuccess(command)
    def _getRefspec(self, fromBranch=None, toBranch=None, force=False):
        returned = ""
        if fromBranch is not None:
            returned += self._normalizeRefName(fromBranch)
        if returned or toBranch is not None:
            returned += ":"
        if toBranch is not None:
            if isinstance(toBranch, branch.RegisteredRemoteBranch):
                toBranch = toBranch.name
            returned += self._normalizeRefName(toBranch)
        if returned and force:
            returned = "+%s" % returned
        return returned
    def push(self, remote=None, fromBranch=None, toBranch=None, force=False):
        command = "git push"
        #build push arguments
        refspec = self._getRefspec(toBranch=toBranch, fromBranch=fromBranch, force=force)

        if refspec and not remote:
            remote = "origin"
        if isinstance(remote, remotes.Remote):
            remote = remote.name
        elif isinstance(remote, RemoteRepository):
            remote = remote.url
        elif isinstance(remote, LocalRepository):
            remote = remote.path
        if remote is not None and not isinstance(remote, basestring):
            raise TypeError("Invalid type for 'remote' parameter: %s" % (type(remote),))
        command = "git push %s %s" % (remote if remote is not None else "", refspec)
        self._executeGitCommandAssertSuccess(command)
    def rebase(self, src):
        self._executeGitCommandAssertSuccess("git rebase %s" % self._normalizeRefName(src))
    #################################### Stashes ###################################
    def saveStash(self, name=None):
        command = "git stash save"
        if name is not None:
            command += " %s" % name
        self._executeGitCommandAssertSuccess(command)
    def popStash(self, arg=None):
        command = "git stash pop"
        if arg is not None:
            command += " %s" % arg
        self._executeGitCommandAssertSuccess(command)
    ################################# Configuration ################################
    def getConfig(self):
        return dict(s.split("=",1) for s in self._getOutputAssertSuccess("git config -l"))

################################### Shortcuts ##################################
def clone(source, location):
    returned = LocalRepository(location)
    returned.clone(source)
    return returned

def find_repository():
    orig_path = path = os.path.realpath('.')
    drive, path = os.path.splitdrive(path)
    while path:
        current_path = os.path.join(drive, path)
        current_repo = LocalRepository(current_path)
        if current_repo.isValid():
            return current_repo
        path, path_tail = os.path.split(current_path)
        if not path_tail:
            raise CannotFindRepository("Cannot find repository for %s" % (orig_path,))
        
