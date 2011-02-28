import os
import sys

def import_path(fullpath):
    """ Import a file with full path specification. Allows one to
        import from anywhere, something __import__ does not do. 
    """
    # http://zephyrfalcon.org/weblog/arch_d7_2002_08_31.html
    path, filename = os.path.split(fullpath)
    filename, ext = os.path.splitext(filename)
    sys.path.append(path)
    module = __import__(filename)
    reload(module) # Might be out of date during tests
    del sys.path[-1]
    return module

