from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent, addEvent, fireEventAsync
from couchpotato.core.helpers.request import jsonified, getParams
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import File
from couchpotato.environment import Env
import os
import time


log = CPLog(__name__)

class Manage(Plugin):

    last_update = 0

    def __init__(self):

        fireEvent('scheduler.interval', identifier = 'manage.update_library', handle = self.updateLibrary, hours = 2)

        addEvent('manage.update', self.updateLibrary)
        addApiView('manage.update', self.updateLibraryView, docs = {
            'desc': 'Update the library by scanning for new movies',
            'params': {
                'full': {'desc': 'Do a full update or just recently changed/added movies.'},
            }
        })

        if not Env.get('dev'):
            addEvent('app.load', self.updateLibrary)

    def updateLibraryView(self):

        params = getParams()

        fireEventAsync('manage.update', full = params.get('full', True))

        return jsonified({
            'success': True
        })


    def updateLibrary(self, full = False):

        if self.isDisabled() or (self.last_update > time.time() - 20):
            return

        directories = self.directories()

        for directory in directories:

            if not os.path.isdir(directory):
                if len(directory) > 0:
                    log.error('Directory doesn\'t exist: %s' % directory)
                continue

            log.info('Updating manage library: %s' % directory)
            fireEvent('scanner.folder', folder = directory)

            # If cleanup option is enabled, remove offline files from database
            if self.conf('cleanup'):
                db = get_session()
                files_in_path = db.query(File).filter(File.path.like(directory + '%%')).filter_by(available = 0).all()
                [db.delete(x) for x in files_in_path]
                db.commit()
                db.remove()

            # Break if CP wants to shut down
            if self.shuttingDown():
                break

        self.last_update = time.time()

    def directories(self):
        try:
            return self.conf('library', default = '').split('::')
        except:
            return []
