from esky import bdist_esky
from setuptools import setup
import os
import sys
import version


# Include proper dirs
base_path = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.join(base_path, 'libs')

sys.path.insert(0, base_path)
sys.path.insert(0, lib_dir)

def getDataFiles(dirs):
    data_files = []
    for directory in dirs:
        for root, dirs, files in os.walk(directory):
            if files:
                for filename in files:
                    if filename[:-4] is not '.pyc':
                        data_files.append((root, [os.path.join(root, filename)]))

    return data_files

includes = [
    'telnetlib',
    'xml.etree.ElementTree',
    'xml.etree.cElementTree',
    'xml.dom',
    'xml.dom.minidom',
    'netrc',
    'csv',
    'HTMLParser',
    'version',
    'distutils',
    'lxml', 'lxml.etree', 'lxml._elementpath', 'gzip',
]

excludes = [
    'doctest',
    'pdb',
    'unittest',
    'difflib',
    'bsddb',
    'pywin.debugger', 'pywin.debugger.dbgcon', 'pywin.dialogs',
    'Tkconstants', 'Tkinter',
    'curses',
    '_gtkagg', '_tkagg',
]

# Windows
if sys.platform == "win32":
    import py2exe

    sys.path.append('C:\Windows\WinSxS\x86_microsoft.vc90.crt_1fc8b3b9a1e18e3b_9.0.21022.8_none_bcb86ed6ac711f91')

    FREEZER = 'py2exe'
    FREEZER_OPTIONS = dict(
        compressed = 0,
        bundle_files = 3,
        dll_excludes = [
            'msvcp90.dll',
            'msvcr90.dll',
            'msvcr71.dll',
            'mswsock.dll',
            'powrprof.dll',
            'USP10.dll',
            'libgdk-win32-2.0-0.dll',
            'libgobject-2.0-0.dll',
            'tcl84.dll',
            'tk84.dll'
        ],
        packages = ['couchpotato', 'libs'],
        includes = includes,
        excludes = excludes,
        skip_archive = 1,
    )
    exeICON = os.path.join(base_path, 'icon.ico')
    DATA_FILES = getDataFiles([r'.\\couchpotato', r'.\\libs'])
    DATA_FILES.append('icon_windows.png')
    file_ext = 'win32.zip'


# OSX
elif sys.platform == "darwin":
    import py2app

    FREEZER = 'py2app'
    FREEZER_OPTIONS = dict(
        arch = 'intel',
        optimize = 0,
        strip = True,
        argv_emulation = False,
        site_packages = False,
        iconfile = 'icon.icns',
        plist = dict(
            LSUIElement = True,
        ),
        packages = ['couchpotato', 'libs'],
        includes = includes,
        excludes = excludes,
    )
    exeICON = None
    DATA_FILES = ['icon_mac.png']

    file_ext = 'macosx-10_6-intel.zip'

# Common
NAME = "CouchPotato"
APP = [bdist_esky.Executable("Desktop.py", name = NAME, icon = exeICON, gui_only = True,)]
ESKY_OPTIONS = dict(
    freezer_module = FREEZER,
    freezer_options = FREEZER_OPTIONS,
    bundle_msvcrt = True,
)

# Build the app and the esky bundle
setup(
    name = NAME,
    scripts = APP,
    version = version.VERSION,
    author = "Ruud",
    author_email = "info@couchpota.to",
    description = 'CouchPotato %s' % version.VERSION,
    data_files = DATA_FILES,
    options = dict(bdist_esky = ESKY_OPTIONS),
)

#distpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
#zipfilename = os.path.join(distpath, '%s-%s.%s' % (NAME, version.VERSION, file_ext))
#zfile = zipfile.ZipFile(zipfilename, "r")
#zfile.extractall(distpath)
