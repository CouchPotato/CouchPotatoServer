from setuptools import setup
setup(
name = 'tvdb_api',
version='1.8.2',

author='dbr/Ben',
description='Interface to thetvdb.com',
url='http://github.com/dbr/tvdb_api/tree/master',
license='unlicense',

long_description="""\
An easy to use API interface to TheTVDB.com
Basic usage is:

>>> import tvdb_api
>>> t = tvdb_api.Tvdb()
>>> ep = t['My Name Is Earl'][1][22]
>>> ep
<Episode 01x22 - Stole a Badge>
>>> ep['episodename']
u'Stole a Badge'
""",

py_modules = ['tvdb_api', 'tvdb_ui', 'tvdb_exceptions', 'tvdb_cache'],

classifiers=[
    "Intended Audience :: Developers",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Topic :: Multimedia",
    "Topic :: Utilities",
    "Topic :: Software Development :: Libraries :: Python Modules",
]
)
