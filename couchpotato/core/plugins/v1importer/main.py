from couchpotato.api import addApiView
from couchpotato.core.event import fireEventAsync
from couchpotato.core.helpers.variable import getImdb
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from flask.globals import request
from flask.helpers import url_for
import os

log = CPLog(__name__)


class V1Importer(Plugin):

    def __init__(self):
        addApiView('v1.import', self.fromOld, methods = ['GET', 'POST'])

    def fromOld(self):

        if request.method != 'POST':
            return self.renderTemplate(__file__, 'form.html', url_for = url_for)

        file = request.files['old_db']

        uploaded_file = os.path.join(Env.get('cache_dir'), 'v1_database.db')

        if os.path.isfile(uploaded_file):
            os.remove(uploaded_file)

        file.save(uploaded_file)

        try:
            import sqlite3
            conn = sqlite3.connect(uploaded_file)

            wanted = []

            t = ('want',)
            cur = conn.execute('SELECT status, imdb FROM Movie WHERE status=?', t)
            for row in cur:
                status, imdb = row
                if getImdb(imdb):
                    wanted.append(imdb)
            conn.close()

            wanted = set(wanted)
            for imdb in wanted:
                fireEventAsync('movie.add', {'identifier': imdb}, search_after = False)

            message = 'Successfully imported %s movie(s)' % len(wanted)
        except Exception, e:
            message = 'Failed: %s' % e

        return self.renderTemplate(__file__, 'form.html', url_for = url_for, message = message)

