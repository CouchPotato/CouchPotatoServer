__all__ = [
    'before_insert',
    'after_insert',
    'before_update',
    'after_update',
    'before_delete',
    'after_delete',
    'reconstructor'
]

def create_decorator(event_name):
    def decorator(func):
        if not hasattr(func, '_elixir_events'):
            func._elixir_events = []
        func._elixir_events.append(event_name)
        return func
    return decorator

before_insert = create_decorator('before_insert')
after_insert = create_decorator('after_insert')
before_update = create_decorator('before_update')
after_update = create_decorator('after_update')
before_delete = create_decorator('before_delete')
after_delete = create_decorator('after_delete')
try:
    from sqlalchemy.orm import reconstructor
except ImportError:
    def reconstructor(func):
        raise Exception('The reconstructor method decorator is only '
                        'available with SQLAlchemy 0.5 and later')
