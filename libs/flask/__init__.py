# -*- coding: utf-8 -*-
"""
    flask
    ~~~~~

    A microframework based on Werkzeug.  It's extensively documented
    and follows best practice patterns.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""

__version__ = '0.9'

# utilities we import from Werkzeug and Jinja2 that are unused
# in the module but are exported as public interface.
from werkzeug.exceptions import abort
from werkzeug.utils import redirect
from jinja2 import Markup, escape

from .app import Flask, Request, Response
from .config import Config
from .helpers import url_for, jsonify, json_available, flash, \
    send_file, send_from_directory, get_flashed_messages, \
    get_template_attribute, make_response, safe_join, \
    stream_with_context
from .globals import current_app, g, request, session, _request_ctx_stack, \
     _app_ctx_stack
from .ctx import has_request_context, has_app_context, \
     after_this_request
from .module import Module
from .blueprints import Blueprint
from .templating import render_template, render_template_string

# the signals
from .signals import signals_available, template_rendered, request_started, \
     request_finished, got_request_exception, request_tearing_down

# only import json if it's available
if json_available:
    from .helpers import json

# backwards compat, goes away in 1.0
from .sessions import SecureCookieSession as Session
