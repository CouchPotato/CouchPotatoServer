import os
from chardet import detect
from couchpotato import Env

fs_enc = Env.get('fs_encoding')


def list_dir(path, full_path = True):
    """
    List directory don't error when it doesn't exist
    """

    path = unicode_path(path)

    if os.path.isdir(path):
        for f in os.listdir(path):
            if full_path:
                yield join(path, f)
            else:
                yield f


def join(*args):
    """
    Join path, encode properly before joining
    """

    return os.path.join(*[safe(x) for x in args])


def unicode_path(path):
    """
    Convert back to unicode
    :param path: path string
    """

    if isinstance(path, str):
        detected = detect(path)
        print detected
        path = path.decode(detected.get('encoding'))
        path = path.decode('unicode_escape')

    return path


def safe(path):

    if isinstance(path, unicode):
        return path.encode('unicode_escape')

    return path
