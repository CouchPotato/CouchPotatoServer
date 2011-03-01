from couchpotato.core.settings.model import Resource
from flask import Module
from flask.helpers import jsonify

api = Module(__name__)

def addApiView(route, func):
    api.add_url_rule(route + '/', route, func)


@api.route('')
def index():
    return jsonify({'test': 'bla'})


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
