import json
import os
import shutil
import tarfile
import time
import traceback
import zipfile
from datetime import datetime
from threading import RLock
import re

from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.helpers.encoding import sp
from couchpotato.core.helpers.variable import removePyc, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from dateutil.parser import parse
from git.repository import LocalRepository
import version
from six.moves import filter


log = CPLog(__name__)


class Updater(Plugin):

    available_notified = False
    _lock = RLock()
    last_check = 'updater.last_checked'

    def __init__(self):

        if Env.get('desktop'):
            self.updater = DesktopUpdater()
        elif os.path.isdir(os.path.join(Env.get('app_dir'), '.git')):
            git_default = 'git'
            git_command = self.conf('git_command', default = git_default)
            git_command = git_command if git_command != git_default and (os.path.isfile(git_command) or re.match('^[a-zA-Z0-9_/\.\-]+$', git_command)) else git_default
            self.updater = GitUpdater(git_command)
        else:
            self.updater = SourceUpdater()

        addEvent('app.load', self.logVersion, priority = 10000)
        addEvent('app.load', self.setCrons)
        addEvent('updater.info', self.info)

        addApiView('updater.info', self.info, docs = {
            'desc': 'Get updater information',
            'return': {
                'type': 'object',
                'example': """{
        'last_check': "last checked for update",
        'update_version': "available update version or empty",
        'version': current_cp_version
}"""}
        })
        addApiView('updater.update', self.doUpdateView)
        addApiView('updater.check', self.checkView, docs = {
            'desc': 'Check for available update',
            'return': {'type': 'see updater.info'}
        })

        addEvent('setting.save.updater.enabled.after', self.setCrons)

    def logVersion(self):
        info = self.info()
        log.info('=== VERSION %s, using %s ===', (info.get('version', {}).get('repr', 'UNKNOWN'), self.updater.getName()))

    def setCrons(self):

        fireEvent('schedule.remove', 'updater.check', single = True)
        if self.isEnabled():
            fireEvent('schedule.interval', 'updater.check', self.autoUpdate, hours = 24)
            self.autoUpdate()  # Check after enabling

    def autoUpdate(self):
        do_check = True

        try:
            last_check = tryInt(Env.prop(self.last_check, default = 0))
            now = tryInt(time.time())
            do_check = last_check < now - 43200

            if do_check:
                Env.prop(self.last_check, value = now)
        except:
            log.error('Failed checking last time to update: %s', traceback.format_exc())

        if do_check and self.isEnabled() and self.check() and self.conf('automatic') and not self.updater.update_failed:

            if self.updater.doUpdate():

                # Notify before restarting
                try:
                    if self.conf('notification'):
                        info = self.updater.info()
                        version_date = datetime.fromtimestamp(info['update_version']['date'])
                        fireEvent('updater.updated', 'CouchPotato: Updated to a new version with hash "%s", this version is from %s' % (info['update_version']['hash'], version_date), data = info)
                except:
                    log.error('Failed notifying for update: %s', traceback.format_exc())

                fireEventAsync('app.restart')

                return True

        return False

    def check(self, force = False):
        if not force and self.isDisabled():
            return

        if self.updater.check():
            if not self.available_notified and self.conf('notification') and not self.conf('automatic'):
                info = self.updater.info()
                version_date = datetime.fromtimestamp(info['update_version']['date'])
                fireEvent('updater.available', message = 'A new update with hash "%s" is available, this version is from %s' % (info['update_version']['hash'], version_date), data = info)
                self.available_notified = True
            return True

        return False

    def info(self, **kwargs):
        self._lock.acquire()

        info = {}
        try:
            info = self.updater.info()
        except:
            log.error('Failed getting updater info: %s', traceback.format_exc())

        self._lock.release()

        return info

    def checkView(self, **kwargs):
        return {
            'update_available': self.check(force = True),
            'info': self.updater.info()
        }

    def doUpdateView(self, **kwargs):

        self.check()
        if not self.updater.update_version:
            log.error('Trying to update when no update is available.')
            success = False
        else:
            success = self.updater.doUpdate()
            if success:
                fireEventAsync('app.restart')

            # Assume the updater handles things
            if not success:
                success = True

        return {
            'success': success
        }

    def doShutdown(self, *args, **kwargs):
        if not Env.get('dev') and not Env.get('desktop'):
            removePyc(Env.get('app_dir'), show_logs = False)

        return super(Updater, self).doShutdown(*args, **kwargs)


class BaseUpdater(Plugin):

    repo_user = 'CouchPotato'
    repo_name = 'CouchPotatoServer'
    branch = version.BRANCH

    version = None
    update_failed = False
    update_version = None
    last_check = 0

    def doUpdate(self):
        pass

    def info(self):

        current_version = self.getVersion()

        return {
            'last_check': self.last_check,
            'update_version': self.update_version,
            'version': current_version,
            'repo_name': '%s/%s' % (self.repo_user, self.repo_name),
            'branch': current_version.get('branch', self.branch),
        }

    def getVersion(self):
        pass

    def check(self):
        pass


class GitUpdater(BaseUpdater):

    old_repo = 'RuudBurger/CouchPotatoServer'
    new_repo = 'CouchPotato/CouchPotatoServer'

    def __init__(self, git_command):
        self.repo = LocalRepository(Env.get('app_dir'), command = git_command)

        remote_name = 'origin'
        remote = self.repo.getRemoteByName(remote_name)
        if self.old_repo in remote.url:
            log.info('Changing repo to new github organization: %s -> %s', (self.old_repo, self.new_repo))
            new_url = remote.url.replace(self.old_repo, self.new_repo)
            self.repo._executeGitCommandAssertSuccess("remote set-url %s %s" % (remote_name, new_url))

    def doUpdate(self):

        try:
            log.info('Updating to latest version')
            self.repo.pull()

            return True
        except:
            log.error('Failed updating via GIT: %s', traceback.format_exc())

        self.update_failed = True

        return False

    def getVersion(self):

        if not self.version:

            hash = None
            date = None
            branch = self.branch

            try:
                output = self.repo.getHead()  # Yes, please
                log.debug('Git version output: %s', output.hash)

                hash = output.hash[:8]
                date = output.getDate()
                branch = self.repo.getCurrentBranch().name
            except Exception as e:
                log.error('Failed using GIT updater, running from source, you need to have GIT installed. %s', e)

            self.version = {
                'repr': 'git:(%s:%s % s) %s (%s)' % (self.repo_user, self.repo_name, branch, hash or 'unknown_hash', datetime.fromtimestamp(date) if date else 'unknown_date'),
                'hash': hash,
                'date': date,
                'type': 'git',
                'branch': branch
            }

        return self.version

    def check(self):

        if self.update_version:
            return True

        log.info('Checking for new version on github for %s', self.repo_name)
        if not Env.get('dev'):
            self.repo.fetch()

        current_branch = self.repo.getCurrentBranch().name

        for branch in self.repo.getRemoteByName('origin').getBranches():
            if current_branch == branch.name:

                local = self.repo.getHead()
                remote = branch.getHead()

                log.debug('Versions, local:%s, remote:%s', (local.hash[:8], remote.hash[:8]))

                if local.getDate() < remote.getDate():
                    self.update_version = {
                        'hash': remote.hash[:8],
                        'date': remote.getDate(),
                    }
                    return True

        self.last_check = time.time()
        return False


class SourceUpdater(BaseUpdater):

    def __init__(self):

        # Create version file in cache
        self.version_file = os.path.join(Env.get('cache_dir'), 'version')
        if not os.path.isfile(self.version_file):
            self.createFile(self.version_file, json.dumps(self.latestCommit()))

    def doUpdate(self):

        try:
            download_data = fireEvent('cp.source_url', repo = self.repo_user, repo_name = self.repo_name, branch = self.branch, single = True)
            destination = os.path.join(Env.get('cache_dir'), self.update_version.get('hash')) + '.' + download_data.get('type')

            extracted_path = os.path.join(Env.get('cache_dir'), 'temp_updater')
            destination = fireEvent('file.download', url = download_data.get('url'), dest = destination, single = True)

            # Cleanup leftover from last time
            if os.path.isdir(extracted_path):
                self.removeDir(extracted_path)
            self.makeDir(extracted_path)

            # Extract
            if download_data.get('type') == 'zip':
                zip_file = zipfile.ZipFile(destination)
                zip_file.extractall(extracted_path)
                zip_file.close()
            else:
                tar = tarfile.open(destination)
                tar.extractall(path = extracted_path)
                tar.close()

            os.remove(destination)

            if self.replaceWith(os.path.join(extracted_path, os.listdir(extracted_path)[0])):
                self.removeDir(extracted_path)

                # Write update version to file
                self.createFile(self.version_file, json.dumps(self.update_version))

                return True
        except:
            log.error('Failed updating: %s', traceback.format_exc())

        self.update_failed = True
        return False

    def replaceWith(self, path):
        path = sp(path)
        app_dir = Env.get('app_dir')
        data_dir = Env.get('data_dir')

        # Get list of files we want to overwrite
        removePyc(app_dir)
        existing_files = []
        for root, subfiles, filenames in os.walk(app_dir):
            for filename in filenames:
                existing_files.append(os.path.join(root, filename))

        for root, subfiles, filenames in os.walk(path):
            for filename in filenames:
                fromfile = os.path.join(root, filename)
                tofile = os.path.join(app_dir, fromfile.replace(path + os.path.sep, ''))

                if not Env.get('dev'):
                    try:
                        if os.path.isfile(tofile):
                            os.remove(tofile)

                        dirname = os.path.dirname(tofile)
                        if not os.path.isdir(dirname):
                            self.makeDir(dirname)

                        shutil.move(fromfile, tofile)
                        try:
                            existing_files.remove(tofile)
                        except ValueError:
                            pass
                    except:
                        log.error('Failed overwriting file "%s": %s', (tofile, traceback.format_exc()))
                        return False

        for still_exists in existing_files:

            if data_dir in still_exists:
                continue

            try:
                os.remove(still_exists)
            except:
                log.error('Failed removing non-used file: %s', traceback.format_exc())

        return True

    def removeDir(self, path):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
        except OSError as inst:
            os.chmod(inst.filename, 0o777)
            self.removeDir(path)

    def getVersion(self):

        if not self.version:
            try:
                f = open(self.version_file, 'r')
                output = json.loads(f.read())
                f.close()

                log.debug('Source version output: %s', output)
                self.version = output
                self.version['type'] = 'source'
                self.version['repr'] = 'source:(%s:%s % s) %s (%s)' % (self.repo_user, self.repo_name, self.branch, output.get('hash', '')[:8], datetime.fromtimestamp(output.get('date', 0)))
            except Exception as e:
                log.error('Failed using source updater. %s', e)
                return {}

        return self.version

    def check(self):

        current_version = self.getVersion()

        try:
            latest = self.latestCommit()

            if latest.get('hash') != current_version.get('hash') and latest.get('date') >= current_version.get('date'):
                self.update_version = latest

            self.last_check = time.time()
        except:
            log.error('Failed updating via source: %s', traceback.format_exc())

        return self.update_version is not None

    def latestCommit(self):
        try:
            url = 'https://api.github.com/repos/%s/%s/commits?per_page=1&sha=%s' % (self.repo_user, self.repo_name, self.branch)
            data = self.getCache('github.commit', url = url)
            commit = json.loads(data)[0]

            return {
                'hash': commit['sha'],
                'date': int(time.mktime(parse(commit['commit']['committer']['date']).timetuple())),
            }
        except:
            log.error('Failed getting latest request from github: %s', traceback.format_exc())

        return {}


class DesktopUpdater(BaseUpdater):

    def __init__(self):
        self.desktop = Env.get('desktop')

    def doUpdate(self):
        try:
            def do_restart(e):
                if e['status'] == 'done':
                    fireEventAsync('app.restart')
                elif e['status'] == 'error':
                    log.error('Failed updating desktop: %s', e['exception'])
                    self.update_failed = True

            self.desktop._esky.auto_update(callback = do_restart)
            return
        except:
            self.update_failed = True

        return False

    def info(self):
        return {
            'last_check': self.last_check,
            'update_version': self.update_version,
            'version': self.getVersion(),
            'branch': self.branch,
        }

    def check(self):
        current_version = self.getVersion()
        try:
            latest = self.desktop._esky.find_update()

            if latest and latest != current_version.get('hash'):
                self.update_version = {
                    'hash': latest,
                    'date': None,
                    'changelog': self.desktop._changelogURL,
                }

            self.last_check = time.time()
        except:
            log.error('Failed updating desktop: %s', traceback.format_exc())

        return self.update_version is not None

    def getVersion(self):
        return {
            'repr': 'desktop: %s' % self.desktop._esky.active_version,
            'hash': self.desktop._esky.active_version,
            'date': None,
            'type': 'desktop',
        }
