from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.plugins.base import Plugin
from flask.globals import request
from flask.helpers import url_for
from flask.templating import render_template_string
import os


class Extension(Plugin):

    def __init__(self):
        addApiView('userscript', self.getExtension)

    def getExtension(self):

        params = {
            'includes': fireEvent('userscript.get_includes', merge = True),
            'excludes': fireEvent('userscript.get_excludes', merge = True),
            'version': self.getVersion(),
            'host': '%s%userscript.add_via_url/' % (request.host_url.rstrip('/'), url_for('api.index')),
        }

        template = open(os.path.join(os.path.dirname(__file__), 'template.js'), 'r').read()
        return render_template_string(template, **params)

    def getVersion(self):

        versions = fireEvent('userscript.get_version')

        version = 0
        for v in versions:
            version += v

        return version
