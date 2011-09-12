from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.request import jsonified
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from git.repository import LocalRepository
import time

log = CPLog(__name__)


class Updater(Plugin):

    repo_name = 'RuudBurger/CouchPotatoServer'

    running = False
    version = None
    update_failed = False
    update_version = None
    last_check = 0

    def __init__(self):

        self.repo = LocalRepository(Env.get('app_dir'))

        fireEvent('schedule.interval', 'updater.check', self.check, hours = 6)

        addEvent('app.load', self.check)

        addApiView('updater.info', self.getInfo)
        addApiView('updater.update', self.doUpdateView)

    def getInfo(self):

        return jsonified({
            'repo_name': self.repo_name,
            'last_check': self.last_check,
            'update_version': self.update_version,
            'version': self.getVersion(),
        })

    def getVersion(self):

        if not self.version:
            try:
                output = self.repo.getHead() # Yes, please
                log.debug('Git version output: %s' % output.hash)
                self.version = output.hash
            except Exception, e:
                log.error('Failed using GIT updater, running from source, you need to have GIT installed. %s' % e)
                return 'No GIT'

        return self.version

    def check(self):

        if self.update_version or self.isDisabled():
            return

        current_branch = self.repo.getCurrentBranch().name

        for branch in self.repo.getRemoteByName('origin').getBranches():
            if current_branch == branch.name:

                local = self.repo.getHead()
                remote = branch.getHead()

                if local.getDate() < remote.getDate():
                    if self.conf('automatic') and not self.update_failed:
                        self.doUpdate()
                    else:
                        self.update_version = remote.hash

        self.last_check = time.time()

    def doUpdateView(self):
        return jsonified({
            'success': self.doUpdate()
        })

    def doUpdate(self):
        try:
            log.info('Updating to latest version');
            self.repo.pull()
            return True
        except Exception, e:
            log.error('Failed updating via GIT: %s' % e)

        self.update_failed = True

        return False

    def isEnabled(self):
        return Plugin.isEnabled(self) and Env.get('uses_git')
