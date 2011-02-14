from couchpotato.core.auth import requires_auth
from couchpotato.core.logger import CPLog
from flask.app import Flask
from flask.globals import request
from flask.helpers import url_for
from flask.module import Module
from flask.templating import render_template
from werkzeug.utils import redirect

app = Flask(__name__)
log = CPLog(__name__)
web = Module(__name__, 'web')


@web.route('/')
@requires_auth
def index():
    return render_template('index.html')

@app.errorhandler(404)
def page_not_found(error):
    index_url = url_for('web.index')
    url = request.path[len(index_url):]
    return redirect(index_url + '#' + url)
