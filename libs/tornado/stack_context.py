#!/usr/bin/env python
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""`StackContext` allows applications to maintain threadlocal-like state
that follows execution as it moves to other execution contexts.

The motivating examples are to eliminate the need for explicit
``async_callback`` wrappers (as in `tornado.web.RequestHandler`), and to
allow some additional context to be kept for logging.

This is slightly magic, but it's an extension of the idea that an
exception handler is a kind of stack-local state and when that stack
is suspended and resumed in a new context that state needs to be
preserved.  `StackContext` shifts the burden of restoring that state
from each call site (e.g.  wrapping each `.AsyncHTTPClient` callback
in ``async_callback``) to the mechanisms that transfer control from
one context to another (e.g. `.AsyncHTTPClient` itself, `.IOLoop`,
thread pools, etc).

Example usage::

    @contextlib.contextmanager
    def die_on_error():
        try:
            yield
        except Exception:
            logging.error("exception in asynchronous operation",exc_info=True)
            sys.exit(1)

    with StackContext(die_on_error):
        # Any exception thrown here *or in callback and its desendents*
        # will cause the process to exit instead of spinning endlessly
        # in the ioloop.
        http_client.fetch(url, callback)
    ioloop.start()

Most applications shouln't have to work with `StackContext` directly.
Here are a few rules of thumb for when it's necessary:

* If you're writing an asynchronous library that doesn't rely on a
  stack_context-aware library like `tornado.ioloop` or `tornado.iostream`
  (for example, if you're writing a thread pool), use
  `.stack_context.wrap()` before any asynchronous operations to capture the
  stack context from where the operation was started.

* If you're writing an asynchronous library that has some shared
  resources (such as a connection pool), create those shared resources
  within a ``with stack_context.NullContext():`` block.  This will prevent
  ``StackContexts`` from leaking from one request to another.

* If you want to write something like an exception handler that will
  persist across asynchronous calls, create a new `StackContext` (or
  `ExceptionStackContext`), and make your asynchronous calls in a ``with``
  block that references your `StackContext`.
"""

from __future__ import absolute_import, division, print_function, with_statement

import sys
import threading

from tornado.util import raise_exc_info


class StackContextInconsistentError(Exception):
    pass


class _State(threading.local):
    def __init__(self):
        self.contexts = (tuple(), None)
_state = _State()


class StackContext(object):
    """Establishes the given context as a StackContext that will be transferred.

    Note that the parameter is a callable that returns a context
    manager, not the context itself.  That is, where for a
    non-transferable context manager you would say::

      with my_context():

    StackContext takes the function itself rather than its result::

      with StackContext(my_context):

    The result of ``with StackContext() as cb:`` is a deactivation
    callback.  Run this callback when the StackContext is no longer
    needed to ensure that it is not propagated any further (note that
    deactivating a context does not affect any instances of that
    context that are currently pending).  This is an advanced feature
    and not necessary in most applications.
    """
    def __init__(self, context_factory):
        self.context_factory = context_factory
        self.contexts = []

    # StackContext protocol
    def enter(self):
        context = self.context_factory()
        self.contexts.append(context)
        context.__enter__()

    def exit(self, type, value, traceback):
        context = self.contexts.pop()
        context.__exit__(type, value, traceback)

    # Note that some of this code is duplicated in ExceptionStackContext
    # below.  ExceptionStackContext is more common and doesn't need
    # the full generality of this class.
    def __enter__(self):
        self.old_contexts = _state.contexts
        self.new_contexts = (self.old_contexts[0] + (self,), self)
        _state.contexts = self.new_contexts

        try:
            self.enter()
        except:
            _state.contexts = self.old_contexts
            raise

    def __exit__(self, type, value, traceback):
        try:
            self.exit(type, value, traceback)
        finally:
            final_contexts = _state.contexts
            _state.contexts = self.old_contexts

            # Generator coroutines and with-statements with non-local
            # effects interact badly.  Check here for signs of
            # the stack getting out of sync.
            # Note that this check comes after restoring _state.context
            # so that if it fails things are left in a (relatively)
            # consistent state.
            if final_contexts is not self.new_contexts:
                raise StackContextInconsistentError(
                    'stack_context inconsistency (may be caused by yield '
                    'within a "with StackContext" block)')


class ExceptionStackContext(object):
    """Specialization of StackContext for exception handling.

    The supplied ``exception_handler`` function will be called in the
    event of an uncaught exception in this context.  The semantics are
    similar to a try/finally clause, and intended use cases are to log
    an error, close a socket, or similar cleanup actions.  The
    ``exc_info`` triple ``(type, value, traceback)`` will be passed to the
    exception_handler function.

    If the exception handler returns true, the exception will be
    consumed and will not be propagated to other exception handlers.
    """
    def __init__(self, exception_handler):
        self.exception_handler = exception_handler

    def exit(self, type, value, traceback):
        if type is not None:
            return self.exception_handler(type, value, traceback)

    def __enter__(self):
        self.old_contexts = _state.contexts
        self.new_contexts = (self.old_contexts[0], self)
        _state.contexts = self.new_contexts

    def __exit__(self, type, value, traceback):
        try:
            if type is not None:
                return self.exception_handler(type, value, traceback)
        finally:
            final_contexts = _state.contexts
            _state.contexts = self.old_contexts

            if final_contexts is not self.new_contexts:
                raise StackContextInconsistentError(
                    'stack_context inconsistency (may be caused by yield '
                    'within a "with StackContext" block)')


class NullContext(object):
    """Resets the `StackContext`.

    Useful when creating a shared resource on demand (e.g. an
    `.AsyncHTTPClient`) where the stack that caused the creating is
    not relevant to future operations.
    """
    def __enter__(self):
        self.old_contexts = _state.contexts
        _state.contexts = (tuple(), None)

    def __exit__(self, type, value, traceback):
        _state.contexts = self.old_contexts


def wrap(fn):
    """Returns a callable object that will restore the current `StackContext`
    when executed.

    Use this whenever saving a callback to be executed later in a
    different execution context (either in a different thread or
    asynchronously in the same thread).
    """
    # Check if function is already wrapped
    if fn is None or hasattr(fn, '_wrapped'):
        return fn

    # Capture current stack head
    contexts = _state.contexts

    #@functools.wraps
    def wrapped(*args, **kwargs):
        try:
            # Force local state - switch to new stack chain
            current_state = _state.contexts
            _state.contexts = contexts

            # Current exception
            exc = (None, None, None)
            top = None

            # Apply stack contexts
            last_ctx = 0
            stack = contexts[0]

            # Apply state
            for n in stack:
                try:
                    n.enter()
                    last_ctx += 1
                except:
                    # Exception happened. Record exception info and store top-most handler
                    exc = sys.exc_info()
                    top = n.old_contexts[1]

            # Execute callback if no exception happened while restoring state
            if top is None:
                try:
                    fn(*args, **kwargs)
                except:
                    exc = sys.exc_info()
                    top = contexts[1]

            # If there was exception, try to handle it by going through the exception chain
            if top is not None:
                exc = _handle_exception(top, exc)
            else:
                # Otherwise take shorter path and run stack contexts in reverse order
                while last_ctx > 0:
                    last_ctx -= 1
                    c = stack[last_ctx]

                    try:
                        c.exit(*exc)
                    except:
                        exc = sys.exc_info()
                        top = c.old_contexts[1]
                        break
                else:
                    top = None

                # If if exception happened while unrolling, take longer exception handler path
                if top is not None:
                    exc = _handle_exception(top, exc)

            # If exception was not handled, raise it
            if exc != (None, None, None):
                raise_exc_info(exc)
        finally:
            _state.contexts = current_state

    wrapped._wrapped = True
    return wrapped


def _handle_exception(tail, exc):
    while tail is not None:
        try:
            if tail.exit(*exc):
                exc = (None, None, None)
        except:
            exc = sys.exc_info()

        tail = tail.old_contexts[1]

    return exc
