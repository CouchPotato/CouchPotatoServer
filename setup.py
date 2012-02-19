from esky import bdist_esky
from setuptools import setup
import sys
import version
import os


# Include proper dirs
base_path = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.join(base_path, 'libs')

sys.path.insert(0, base_path)
sys.path.insert(0, lib_dir)



# Windows
if sys.platform == "win32":
    import py2exe

    FREEZER = 'py2exe'
    FREEZER_OPTIONS = dict(
        compressed = 0,
        optimize = 0,
        bundle_files = 3,
        dll_excludes = [
            'MSVCP90.dll',
            'mswsock.dll',
            'powrprof.dll',
            'USP10.dll',
        ],
        packages = ['couchpotato', 'libs'],
        includes = [
            'telnetlib',
            'xml.etree.ElementTree',
            'xml.etree.cElementTree',
            'xml.dom',
            'xml.dom.minidom',
        ],
    )
    exeICON = 'icon.ico'


# OSX
elif sys.platform == "darwin":
    import py2app

    FREEZER = 'py2app'
    FREEZER_OPTIONS = dict(
        argv_emulation = False,
        iconfile = 'icon.icns',
        plist = dict(
            LSUIElement = True,
        ),
        packages = ['couchpotato', 'libs'],
        includes = [
            'telnetlib',
            'xml.etree.ElementTree',
            'xml.etree.cElementTree',
            'xml.dom',
            'xml.dom.minidom',
        ],
    )
    exeICON = None

# Common
NAME = "CouchPotato"
APP = [bdist_esky.Executable("Desktop.py", name = NAME, gui_only = True, icon = exeICON,)]
DATA_FILES = ['icon.ico']
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
    data_files = DATA_FILES,
    options = dict(bdist_esky = ESKY_OPTIONS),
)


