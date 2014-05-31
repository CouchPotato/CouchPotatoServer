def try_convert(value, to_type, default=None):
    try:
        return to_type(value)
    except ValueError:
        return default
    except TypeError:
        return default
