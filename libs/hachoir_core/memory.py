import gc

#---- Default implementation when resource is missing ----------------------
PAGE_SIZE = 4096

def getMemoryLimit():
    """
    Get current memory limit in bytes.

    Return None on error.
    """
    return None

def setMemoryLimit(max_mem):
    """
    Set memory limit in bytes.
    Use value 'None' to disable memory limit.

    Return True if limit is set, False on error.
    """
    return False

def getMemorySize():
    """
    Read currenet process memory size: size of available virtual memory.
    This value is NOT the real memory usage.

    This function only works on Linux (use /proc/self/statm file).
    """
    try:
        statm = open('/proc/self/statm').readline().split()
    except IOError:
        return None
    return int(statm[0]) * PAGE_SIZE

def clearCaches():
    """
    Try to clear all caches: call gc.collect() (Python garbage collector).
    """
    gc.collect()
    #import re; re.purge()

try:
#---- 'resource' implementation ---------------------------------------------
    from resource import getpagesize, getrlimit, setrlimit, RLIMIT_AS

    PAGE_SIZE = getpagesize()

    def getMemoryLimit():
        try:
            limit = getrlimit(RLIMIT_AS)[0]
            if 0 < limit:
                limit *= PAGE_SIZE
            return limit
        except ValueError:
            return None

    def setMemoryLimit(max_mem):
        if max_mem is None:
            max_mem = -1
        try:
            setrlimit(RLIMIT_AS, (max_mem, -1))
            return True
        except ValueError:
            return False
except ImportError:
    pass

def limitedMemory(limit, func, *args, **kw):
    """
    Limit memory grow when calling func(*args, **kw):
    restrict memory grow to 'limit' bytes.

    Use try/except MemoryError to catch the error.
    """
    # First step: clear cache to gain memory
    clearCaches()

    # Get total program size
    max_rss = getMemorySize()
    if max_rss is not None:
        # Get old limit and then set our new memory limit
        old_limit = getMemoryLimit()
        limit = max_rss + limit
        limited = setMemoryLimit(limit)
    else:
        limited = False

    try:
        # Call function
        return func(*args, **kw)
    finally:
        # and unset our memory limit
        if limited:
            setMemoryLimit(old_limit)

        # After calling the function: clear all caches
        clearCaches()

