import warnings
import os, sys
from twisted.python.procutils import which

def find_exe(exename):
    """
    Look for something named exename or exename + ".py".

    This is a kludge.

    @return: a list containing one element which is the path to the exename
        (if it is thought to be executable), or else the first element being
        sys.executable and the second element being the path to the
        exename + ".py", or else return False if one can't be found
    """
    warnings.warn("deprecated", DeprecationWarning)
    exes = which(exename)
    exe = exes and exes[0]
    if not exe:
        exe = os.path.join(sys.prefix, 'scripts', exename + '.py')
    if os.path.exists(exe):
        path, ext = os.path.splitext(exe)
        if ext.lower() in [".exe", ".bat",]:
            cmd = [exe,]
        else:
            cmd = [sys.executable, exe,]
        return cmd
    else:
        return False

