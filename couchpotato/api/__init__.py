from flask import Module
from flask.helpers import jsonify

api = Module(__name__)

@api.route('/')
def index():
    return jsonify({'test': 'bla'})
