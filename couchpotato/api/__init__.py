from flask import Module

api = Module(__name__)

@api.route('/')
def index():
    return 'api'
