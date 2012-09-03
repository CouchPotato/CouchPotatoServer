from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent, fireEventAsync
from couchpotato.core.helpers.encoding import ss
from couchpotato.core.helpers.request import jsonified
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from datetime import datetime
from dateutil.parser import parse
from git.repository import LocalRepository
import json
import os
import shutil
import tarfile
import time
import traceback
import version

log = CPLog(__name__)


class Updater(Plugin):

    available_notified = False

    def __init__(self):

        if Env.get('desktop'):
            self.updater = DesktopUpdater()
        elif os.path.isdir(os.path.join(Env.get('app_dir'), '.git')):
            self.updater = GitUpdater(self.conf('git_command', default = 'git'))
        else:
            self.updater = SourceUpdater()

        fireEvent('schedule.interval', 'updater.check', self.autoUpdate, hours = 6)
        addEvent('app.load', self.autoUpdate)
        addEvent('updater.info', self.info)

        addApiView('updater.info', self.getInfo, docs = {
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

    def autoUpdate(self):
        if self.check() and self.conf('automatic') and not self.updater.update_failed:
            if self.updater.doUpdate():

                # Notify before restarting
                try:
                    if self.conf('notification'):
                        info = self.updater.info()
                        version_date = datetime.fromtimestamp(info['update_version']['date'])
                        fireEvent('updater.updated', 'Updated to a new version with hash "%s", this version is from %s' % (info['update_version']['hash'], version_date), data = info)
                except:
                    log.error('Failed notifying for update: %s', traceback.format_exc())

                fireEventAsync('app.restart')

                return True

        return False

    def check(self):
        if self.isDisabled():
            return

        if self.updater.check():
            if not self.available_notified and self.conf('notification') and not self.conf('automatic'):
                fireEvent('updater.available', message = 'A new update is available', data = self.updater.info())
                self.available_notified = True
            return True

        return False

    def info(self):
        return self.updater.info()

    def getInfo(self):
        return jsonified(self.updater.info())

    def checkView(self):
        return jsonified({
            'update_available': self.check(),
            'info': self.updater.info()
        })

    def doUpdateView(self):

        self.check()
        if not self.updater.update_version:
            log.error('Trying to update when no update is available.')
            success = False
        else:
            success = self.updater.doUpdate()
            if success:
                fireEventAsync('app.restart')

        return jsonified({
            'success': success
        })


class BaseUpdater(Plugin):

    repo_user = 'RuudBurger'
    repo_name = 'CouchPotatoServer'
    branch = version.BRANCH

    version = None
    update_failed = False
    update_version = None
    last_check = 0

    def doUpdate(self):
        pass

    def getInfo(self):
        return jsonified(self.info())

    def info(self):
        return {
            'last_check': self.last_check,
            'update_version': self.update_version,
            'version': self.getVersion(),
            'repo_name': '%s/%s' % (self.repo_user, self.repo_name),
            'branch': self.branch,
        }

    def check(self):
        pass

    def deletePyc(self, only_excess = True):

        for root, dirs, files in os.walk(ss(Env.get('app_dir'))):

            pyc_files = filter(lambda filename: filename.endswith('.pyc'), files)
            py_files = set(filter(lambda filename: filename.endswith('.py'), files))
            excess_pyc_files = filter(lambda pyc_filename: pyc_filename[:-1] not in py_files, pyc_files) if only_excess else pyc_files

            for excess_pyc_file in excess_pyc_files:
                full_path = os.path.join(root, excess_pyc_file)
                log.debug('Removing old PYC file: %s', full_path)
                try:
                    os.remove(full_path)
                except:
                    log.error('Couldn\'t remove %s: %s', (full_path, traceback.format_exc()))

            for dir_name in dirs:
                full_path = os.path.join(root, dir_name)
                if len(os.listdir(full_path)) == 0:
                    try:
                        os.rmdir(full_path)
                    except:
                        log.error('Couldn\'t remove empty directory %s: %s', (full_path, traceback.format_exc()))



class GitUpdater(BaseUpdater):

    def __init__(self, git_command):
        self.repo = LocalRepository(Env.get('app_dir'), command = git_command)

    def doUpdate(self):

        try:
            log.debug('Stashing local changes')
            self.repo.saveStash()

            log.info('Updating to latest version')
            self.repo.pull()

            # Delete leftover .pyc files
            self.deletePyc()

            return True
        except:
            log.error('Failed updating via GIT: %s', traceback.format_exc())

        self.update_failed = True

        return False

    def getVersion(self):

        if not self.version:
            try:
                output = self.repo.getHead() # Yes, please
                log.debug('Git version output: %s', output.hash)
                self.version = {
                    'hash': output.hash[:8],
                    'date': output.getDate(),
                    'type': 'git',
                }
            except Exception, e:
                log.error('Failed using GIT updater, running from source, you need to have GIT installed. %s', e)
                return 'No GIT'

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

                log.info('Versions, local:%s, remote:%s', (local.hash[:8], remote.hash[:8]))

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
            url = 'https://github.com/%s/%s/tarball/%s' % (self.repo_user, self.repo_name, self.branch)
            destination = os.path.join(Env.get('cache_dir'), self.update_version.get('hash') + '.tar.gz')
            extracted_path = os.path.join(Env.get('cache_dir'), 'temp_updater')

            destination = fireEvent('file.download', url = url, dest = destination, single = True)

            # Cleanup leftover from last time
            if os.path.isdir(extracted_path):
                self.removeDir(extracted_path)
            self.makeDir(extracted_path)

            # Extract
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
        app_dir = ss(Env.get('app_dir'))

        # Get list of files we want to overwrite
        self.deletePyc()
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

        if Env.get('app_dir') not in Env.get('data_dir'):
            for still_exists in existing_files:
                try:
                    os.remove(still_exists)
                except:
                    log.error('Failed removing non-used file: %s', traceback.format_exc())

        return True


    def removeDir(self, path):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
        except OSError, inst:
            os.chmod(inst.filename, 0777)
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
            except Exception, e:
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
                'date':  int(time.mktime(parse(commit['commit']['committer']['date']).timetuple())),
            }
        except:
            log.error('Failed getting latest request from github: %s', traceback.format_exc())

        return {}


class DesktopUpdater(BaseUpdater):

    version = None
    update_failed = False
    update_version = None
    last_check = 0

    def __init__(self):
        self.desktop = Env.get('desktop')

    def doUpdate(self):
        try:
            def do_restart(e):
                if e['status'] == 'done':
                    fireEventAsync('app.restart')
                else:
                    log.error('Failed updating desktop: %s', e['exception'])
                    self.update_failed = True

            self.desktop._esky.auto_update(callback = do_restart)
        except:
            self.update_failed = True

        return False

    def info(self):
        return {
            'last_check': self.last_check,
            'update_version': self.update_version,
            'version': self.getVersion(),
            'branch': 'desktop_build',
        }

    def check(self):
        current_version = self.getVersion()
        try:
            latest = self.desktop._esky.find_update()

            if latest and latest != current_version.get('hash'):
                self.update_version = {
                    'hash': latest,
                    'date':  None,
                    'changelog': self.desktop._changelogURL,
                }

            self.last_check = time.time()
        except:
            log.error('Failed updating desktop: %s', traceback.format_exc())

        return self.update_version is not None

    def getVersion(self):
        return {
            'hash': self.desktop._esky.active_version,
            'date': None,
            'type': 'desktop',
        }
