import sqlalchemy as sa
from sqlalchemy import orm


class DatabaseError(Exception):
    """Custom exceptions related to the database."""
    pass


def _session_cls_cache(cache={}):
    """Holds a dictionary to cache session objects."""
    return cache


def get_session(engine=None, test=False):
    """
    Get the current session or create a new one based on the engine.

    >>> from couchpotato import db
    >>> from sqlalchemy import create_engine
    >>> engine = create_engine('sqlite:///:memory:')
    >>> session = db.get_session(engine)
    >>> session #doctest: +ELLIPSIS
    <sqlalchemy.orm.session.Session object at ...>

    Once a session has been created, get_session will return session instances
    of the same Session class.
    >>> type(session) == type(db.get_session())
    True

    If you create multiple sessions for different engines, you need to
    specify which session you want by passing the engine explicitely.

    >>> other_engine = create_engine('sqlite:///:memory:')
    >>> other_session = db.get_session(other_engine)
    >>> type(other_session) is type(db.get_session(other_engine))
    True

    """
    cache = _session_cls_cache()

    assert not(engine and test), "Cannot pass both test and engine."
    # It doesn't make sense to both pass an engine and instruct the function
    # to create a new engine.  Decide what you want to do, but not both.
    if test:
        in_memory = sa.create_engine('sqlite:///:memory:')
        session = orm.sessionmaker(bind=in_memory)()
        # create Session class ^               ^
        #              create Session instance ^
    elif engine:
        key = (engine, )
        if key not in cache:
            cache[key] = orm.sessionmaker(bind=engine)
        session = cache[key]()
    elif len(cache) == 1:
        session = (cache[key] for key in cache).next()()
        #             return the first element ^     ^
        #                        instantiate session ^
    elif len(cache) >= 1:
        raise DatabaseError("Multiple Session classes found. Choose one.")
    else:
        raise DatabaseError("No session found. You need to create one.")

    return session
