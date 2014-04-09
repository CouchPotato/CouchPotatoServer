from __future__ import absolute_import
from __future__ import print_function

import re
import sys
import time

import six

from scss import config


def split_params(params):
    params = params.split(',') or []
    if params:
        final_params = []
        param = params.pop(0)
        try:
            while True:
                while param.count('(') != param.count(')'):
                    try:
                        param = param + ',' + params.pop(0)
                    except IndexError:
                        break
                final_params.append(param)
                param = params.pop(0)
        except IndexError:
            pass
        params = final_params
    return params


def dequote(s):
    if s and s[0] in ('"', "'") and s[-1] == s[0]:
        s = s[1:-1]
        s = unescape(s)
    return s


def depar(s):
    while s and s[0] == '(' and s[-1] == ')':
        s = s[1:-1]
    return s


def to_str(num):
    try:
        render = num.render
    except AttributeError:
        pass
    else:
        return render()

    if isinstance(num, dict):
        s = sorted(num.items())
        sp = num.get('_', '')
        return (sp + ' ').join(to_str(v) for n, v in s if n != '_')
    elif isinstance(num, float):
        num = ('%0.05f' % round(num, 5)).rstrip('0').rstrip('.')
        return num
    elif isinstance(num, bool):
        return 'true' if num else 'false'
    elif num is None:
        return ''
    return str(num)


def to_float(num):
    if isinstance(num, (float, int)):
        return float(num)
    num = to_str(num)
    if num and num[-1] == '%':
        return float(num[:-1]) / 100.0
    else:
        return float(num)


def escape(s):
    return re.sub(r'''(["'])''', r'\\\1', s)


def unescape(s):
    return re.sub(r'''\\(['"])''', r'\1', s)


def normalize_var(var):
    """Sass defines `foo_bar` and `foo-bar` as being identical, both in
    variable names and functions/mixins.  This normalizes everything to use
    dashes.
    """
    return var.replace('_', '-')


################################################################################
# Function timing decorator
profiling = {}


def print_timing(level=0):
    def _print_timing(func):
        if config.VERBOSITY:
            def wrapper(*args, **kwargs):
                if config.VERBOSITY >= level:
                    t1 = time.time()
                    res = func(*args, **kwargs)
                    t2 = time.time()
                    profiling.setdefault(func.func_name, 0)
                    profiling[func.func_name] += (t2 - t1)
                    return res
                else:
                    return func(*args, **kwargs)
            return wrapper
        else:
            return func
    return _print_timing


################################################################################
# Profiler decorator
def profile(fn):
    import cProfile
    import pstats
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        stream = six.StringIO()
        profiler.enable()
        try:
            res = fn(*args, **kwargs)
        finally:
            profiler.disable()
            stats = pstats.Stats(profiler, stream=stream)
            stats.sort_stats('time')
            print >>stream, ""
            print >>stream, "=" * 100
            print >>stream, "Stats:"
            stats.print_stats()
            print >>stream, "=" * 100
            print >>stream, "Callers:"
            stats.print_callers()
            print >>stream, "=" * 100
            print >>stream, "Callees:"
            stats.print_callees()
            print >>sys.stderr, stream.getvalue()
            stream.close()
        return res
    return wrapper
