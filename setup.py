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
]

# Windows
if sys.platform == "win32":
    import py2exe

    FREEZER = 'py2exe'
    FREEZER_OPTIONS = dict(
        compressed = 0,
        bundle_files = 3,
        dll_excludes = [
            'MSVCP90.dll',
            'mswsock.dll',
            'powrprof.dll',
            'USP10.dll',
        ],
        packages = ['couchpotato', 'libs'],
        includes = includes,
        skip_archive = 1,
    )
    exeICON = os.path.join(base_path, 'icon.ico')
    DATA_FILES = getDataFiles([r'.\\couchpotato', r'.\\libs'])
    DATA_FILES.append('icon.png')
    file_ext = 'win32.zip'


# OSX
elif sys.platform == "darwin":
    import py2app

    FREEZER = 'py2app'
    FREEZER_OPTIONS = dict(
        optimize = 2,
        strip = True,
        argv_emulation = False,
        site_packages = False,
        iconfile = 'icon.icns',
        plist = dict(
            LSUIElement = True,
        ),
        packages = ['couchpotato', 'libs'],
        includes = includes,
    )
    exeICON = None
    DATA_FILES = ['icon.png']

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
