import logging

def add_coloring_to_emit_ansi(fn):
    def new(*args):
        levelno = args[1].levelno
        if(levelno >= 50):
            color = '\x1b[31m' # red
        elif(levelno >= 40):
            color = '\x1b[31m' # red
        elif(levelno >= 30):
            color = '\x1b[33m' # yellow
        elif(levelno >= 20):
            color = '\x1b[0m'
        elif(levelno >= 10):
            color = '\x1b[36m'
        else:
            color = '\x1b[0m'  # normal

        if not args[1].msg.startswith(color):
            args[1].msg = color + args[1].msg + '\x1b[0m'

        return fn(*args)
    return new

logging.StreamHandler.emit = add_coloring_to_emit_ansi(logging.StreamHandler.emit)
