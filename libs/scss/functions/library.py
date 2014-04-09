"""Defines `FunctionLibrary`, a class that collects functions to be exposed to
SCSS during compilation.
"""

# TODO the constant versions of this should be frozen
class FunctionLibrary(object):
    """Contains a set of functions to be exposed to SCSS.

    Functions are keyed by both their name _and_ arity; this allows for
    function overloading somewhat beyond what Python easily allows, and is
    required for several functions in the standard Sass library.

    Functions may also have arbitrary arity, in which case they accept any
    number of arguments, though a function of the same name with a specific
    arity takes precedence.
    """

    def __init__(self):
        self._functions = {}

    def derive(self):
        """Returns a new registry object, pre-populated with all the functions
        in this registry.
        """
        new = type(self)()
        new.inherit(self)
        return new

    def inherit(self, *other_libraries):
        """Import all the functions from the given other libraries into this one.

        Note that existing functions ARE NOT replaced -- which also means that
        functions from the first library take precedence over functions from
        the second library, etc.
        """
        new_functions = dict()

        # dict.update replaces keys; go through the other libraries in reverse,
        # so the first one wins
        for library in reversed(other_libraries):
            new_functions.update(library._functions)

        new_functions.update(self._functions)
        self._functions = new_functions

    def register(self, name, argc=None):
        """Decorator for adding a function to this library."""
        # XXX: this should allow specifying names of keyword arguments, as
        # well.  currently none of these functions support kwargs, i think.
        # XXX automatically inferring the name and args would be...
        # interesting
        # XXX also it would be nice if a function which EXISTS but has the
        # wrong number of args threw a useful error; atm i think it'll become
        # literal (yikes!)

        key = (name, argc)

        def decorator(f):
            self._functions[key] = f
            return f

        return decorator

    def add(self, function, name, argc=None):
        """Add a function to this library imperatively."""

        key = (name, argc)
        self._functions[key] = function

    def lookup(self, name, argc=None):
        """Find a function given its name and the number of arguments it takes.
        Falls back to a function with the same name that takes any number of
        arguments.
        """
        # Try the given arity first
        key = name, argc
        if key in self._functions:
            return self._functions[key]

        # Fall back to arbitrary-arity (or KeyError if neither exists)
        return self._functions[name, None]
