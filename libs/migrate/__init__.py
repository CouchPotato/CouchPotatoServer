"""
   SQLAlchemy migrate provides two APIs :mod:`migrate.versioning` for
   database schema version and repository management and
   :mod:`migrate.changeset` that allows to define database schema changes
   using Python.
"""

from migrate.versioning import *
from migrate.changeset import *

__version__ = '0.7.2'
