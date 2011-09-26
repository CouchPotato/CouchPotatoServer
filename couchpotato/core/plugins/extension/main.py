from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.plugins.base import Plugin
from flask.helpers import url_for
from flask.templating import render_template


class Extension(Plugin):

    def __init__(self):
        addApiView('extension.user.js', self.getExtension)

    def getExtension(self):

        params = {
            'includes': fireEvent('extension.get_includes', single = True),
            'excludes': fireEvent('extension.get_includes', single = True),
            'version': self.getVersion(),
            'host': '%s/extension.add_via_url' % url_for('api.index'),
        }

        return render_template('template.js', **params)

    def getVersion(self):

        versions = fireEvent('extension.get_version')

        version = 0
        for v in versions:
            version += v

        return version
