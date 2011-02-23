from couchpotato.api.file_browser import FileBrowser
from couchpotato.core.settings.loader import settings_loader
from couchpotato.core.settings.model import Resource
from couchpotato.environment import Env
from flask import Module
from flask.helpers import jsonify
import flask

api = Module(__name__)

@api.route('')
def index():
    return jsonify({'test': 'bla'})


@api.route('settings/')
def settings_view():
    return jsonify({
        'sections': settings_loader.sections,
        'values': Env.get('settings').getValues()
    })

@api.route('setting.save/')
def setting_save_view():
    a = flask.request.args

    section = a.get('section')
    option = a.get('name')
    value = a.get('value')

    Env.get('settings').set(section, option, value)
    Env.get('settings').save()

    return jsonify({
        'success': True,
    });

@api.route('movie/')
def movie():

    return jsonify({
        'success': True,
        'movies': [
            {
                'name': 'Movie 1',
                'description': 'Description 1',
            },
            {
                'name': 'Movie 2',
                'description': 'Description 2',
            }
        ]
    })

@api.route('directory.list/')
def director_list():
    a = flask.request.args

    try:
        fb = FileBrowser(a.get('path', '/'))
        dirs = fb.getDirectories()
    except:
        dirs = []

    return jsonify({
        'empty': len(dirs) == 0,
        'dirs': dirs,
    })
