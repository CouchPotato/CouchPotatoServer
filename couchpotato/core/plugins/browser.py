import ctypes
import os
import string
import traceback
import time

from couchpotato import CPLog
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import sp, ss, toUnicode
from couchpotato.core.helpers.variable import getUserDir
from couchpotato.core.plugins.base import Plugin

from couchpotato.environment import Env

log = CPLog(__name__)

if os.name == 'nt':
    import imp
    try:
        imp.find_module('win32file')
    except:
        # todo:: subclass ImportError for missing dependencies, vs. broken plugins?
        raise ImportError("Missing the win32file module, which is a part of the prerequisite \
            pywin32 package. You can get it from http://sourceforge.net/projects/pywin32/files/pywin32/")
    else:
        # noinspection PyUnresolvedReferences
        import win32file

autoload = 'FileBrowser'

class FileBrowser(Plugin):

    def __init__(self):
        addApiView('directory.list', self.view, docs = {
            'desc': 'Return the directory list of a given directory',
            'params': {
                'path': {'desc': 'The directory to scan'},
                'show_hidden': {'desc': 'Also show hidden files'}
            },
            'return': {'type': 'object', 'example': """{
    'is_root': bool, //is top most folder
    'parent': string, //parent folder of requested path
    'home': string, //user home folder
    'empty': bool, //directory is empty
    'dirs': array, //directory names
}"""}
        })

    def getDirectories(self, path = '/', show_hidden = True):

        # Return driveletters or root if path is empty
        if path == '/' or not path or path == '\\':
            if os.name == 'nt':
                return self.getDriveLetters()
            path = '/'

        dirs = []
        path = sp(path)
        for f in os.listdir(path):
            p = sp(os.path.join(path, f))
            if os.path.isdir(p) and ((self.is_hidden(p) and bool(int(show_hidden))) or not self.is_hidden(p)):
                dirs.append(toUnicode('%s%s' % (p, os.path.sep)))

        return sorted(dirs)

    def getFiles(self):
        pass

    def getDriveLetters(self):

        driveletters = []
        for drive in string.ascii_uppercase:
            if win32file.GetDriveType(drive + ':') in [win32file.DRIVE_FIXED, win32file.DRIVE_REMOTE, win32file.DRIVE_RAMDISK, win32file.DRIVE_REMOVABLE]:
                driveletters.append(drive + ':\\')

        return driveletters

    def view(self, path = '/', show_hidden = True, **kwargs):

        soft_chroot = Env.get('softchroot')
        
        home = getUserDir()
        if soft_chroot.enabled:
            if not soft_chroot.is_subdir(home):
                home = soft_chroot.get_chroot()

        if not path:
            path = home
            if path.endswith(os.path.sep):
                path = path.rstrip(os.path.sep)
        else:
            path = soft_chroot.chroot2abs(path)

        try:
            dirs = self.getDirectories(path = path, show_hidden = show_hidden)
        except:
            log.error('Failed getting directory "%s" : %s', (path, traceback.format_exc()))
            dirs = []

        if soft_chroot.enabled:
            dirs = map(soft_chroot.abs2chroot, dirs)

        parent = os.path.dirname(path.rstrip(os.path.sep))
        if parent == path.rstrip(os.path.sep):
            parent = '/'
        elif parent != '/' and parent[-2:] != ':\\':
            parent += os.path.sep

        # TODO : check on windows:
        is_root = path == '/'

        if soft_chroot.enabled:
            is_root = soft_chroot.is_root_abs(path)

            # fix paths:
            if soft_chroot.is_subdir(parent):
                parent = soft_chroot.abs2chroot(parent)
            else:
                parent = os.path.sep

            home = soft_chroot.abs2chroot(home)

        return {
            'is_root': is_root,
            'empty': len(dirs) == 0,
            'parent': parent,
            'home': home,
            'platform': os.name,
            'dirs': dirs,
        }


    def is_hidden(self, filepath):
        name = ss(os.path.basename(os.path.abspath(filepath)))
        return name.startswith('.') or self.has_hidden_attribute(filepath)

    def has_hidden_attribute(self, filepath):

        result = False
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(sp(filepath)) #@UndefinedVariable
            assert attrs != -1
            result = bool(attrs & 2)
        except (AttributeError, AssertionError):
            pass
        except:
            log.error('Failed getting hidden attribute: %s', traceback.format_exc())

        return result
