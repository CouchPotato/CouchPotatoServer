"""
parser.sql.objectadapter module (imdb.parser.sql package).

This module adapts the SQLObject ORM to the internal mechanism.

Copyright 2008-2010 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import sys
import logging

from sqlobject import *
from sqlobject.sqlbuilder import ISNULL, ISNOTNULL, AND, OR, IN, CONTAINSSTRING

from dbschema import *

_object_logger = logging.getLogger('imdbpy.parser.sql.object')


# Maps our placeholders to SQLAlchemy's column types.
MAP_COLS = {
        INTCOL: IntCol,
        UNICODECOL: UnicodeCol,
        STRINGCOL: StringCol
}


# Exception raised when Table.get(id) returns no value.
NotFoundError = SQLObjectNotFound


# class method to be added to the SQLObject class.
def addIndexes(cls, ifNotExists=True):
    """Create all required indexes."""
    for col in cls._imdbpySchema.cols:
        if col.index:
            idxName = col.index
            colToIdx = col.name
            if col.indexLen:
                colToIdx = {'column': col.name, 'length': col.indexLen}
            if idxName in [i.name for i in cls.sqlmeta.indexes]:
                # Check if the index is already present.
                continue
            idx = DatabaseIndex(colToIdx, name=idxName)
            cls.sqlmeta.addIndex(idx)
    try:
        cls.createIndexes(ifNotExists)
    except dberrors.OperationalError, e:
        _object_logger.warn('Skipping creation of the %s.%s index: %s' %
                            (cls.sqlmeta.table, col.name, e))
addIndexes = classmethod(addIndexes)


# Global repository for "fake" tables with Foreign Keys - need to
# prevent troubles if addForeignKeys is called more than one time.
FAKE_TABLES_REPOSITORY = {}

def _buildFakeFKTable(cls, fakeTableName):
    """Return a "fake" table, with foreign keys where needed."""
    countCols = 0
    attrs = {}
    for col in cls._imdbpySchema.cols:
        countCols += 1
        if col.name == 'id':
            continue
        if not col.foreignKey:
            # A non-foreign key column - add it as usual.
            attrs[col.name] = MAP_COLS[col.kind](**col.params)
            continue
        # XXX: Foreign Keys pointing to TableName.ColName not yet supported.
        thisColName = col.name
        if thisColName.endswith('ID'):
            thisColName = thisColName[:-2]

        fks = col.foreignKey.split('.', 1)
        foreignTableName = fks[0]
        if len(fks) == 2:
            foreignColName = fks[1]
        else:
            foreignColName = 'id'
        # Unused...
        #fkName = 'fk_%s_%s_%d' % (foreignTableName, foreignColName,
        #                        countCols)
        # Create a Foreign Key column, with the correct references.
        fk = ForeignKey(foreignTableName, name=thisColName, default=None)
        attrs[thisColName] = fk
    # Build a _NEW_ SQLObject subclass, with foreign keys, if needed.
    newcls = type(fakeTableName, (SQLObject,), attrs)
    return newcls

def addForeignKeys(cls, mapTables, ifNotExists=True):
    """Create all required foreign keys."""
    # Do not even try, if there are no FK, in this table.
    if not filter(None, [col.foreignKey for col in cls._imdbpySchema.cols]):
        return
    fakeTableName = 'myfaketable%s' % cls.sqlmeta.table
    if fakeTableName in FAKE_TABLES_REPOSITORY:
        newcls = FAKE_TABLES_REPOSITORY[fakeTableName]
    else:
        newcls = _buildFakeFKTable(cls, fakeTableName)
        FAKE_TABLES_REPOSITORY[fakeTableName] = newcls
    # Connect the class with foreign keys.
    newcls.setConnection(cls._connection)
    for col in cls._imdbpySchema.cols:
        if col.name == 'id':
            continue
        if not col.foreignKey:
            continue
        # Get the SQL that _WOULD BE_ run, if we had to create
        # this "fake" table.
        fkQuery = newcls._connection.createReferenceConstraint(newcls,
                                newcls.sqlmeta.columns[col.name])
        if not fkQuery:
            # Probably the db doesn't support foreign keys (SQLite).
            continue
        # Remove "myfaketable" to get references to _real_ tables.
        fkQuery = fkQuery.replace('myfaketable', '')
        # Execute the query.
        newcls._connection.query(fkQuery)
    # Disconnect it.
    newcls._connection.close()
addForeignKeys = classmethod(addForeignKeys)


# Module-level "cache" for SQLObject classes, to prevent
# "class TheClass is already in the registry" errors, when
# two or more connections to the database are made.
# XXX: is this the best way to act?
TABLES_REPOSITORY = {}

def getDBTables(uri=None):
    """Return a list of classes to be used to access the database
    through the SQLObject ORM.  The connection uri is optional, and
    can be used to tailor the db schema to specific needs."""
    DB_TABLES = []
    for table in DB_SCHEMA:
        if table.name in TABLES_REPOSITORY:
            DB_TABLES.append(TABLES_REPOSITORY[table.name])
            continue
        attrs = {'_imdbpyName': table.name, '_imdbpySchema': table,
                'addIndexes': addIndexes, 'addForeignKeys': addForeignKeys}
        for col in table.cols:
            if col.name == 'id':
                continue
            attrs[col.name] = MAP_COLS[col.kind](**col.params)
        # Create a subclass of SQLObject.
        # XXX: use a metaclass?  I can't see any advantage.
        cls = type(table.name, (SQLObject,), attrs)
        DB_TABLES.append(cls)
        TABLES_REPOSITORY[table.name] = cls
    return DB_TABLES


def toUTF8(s):
    """For some strange reason, sometimes SQLObject wants utf8 strings
    instead of unicode."""
    return s.encode('utf_8')


def setConnection(uri, tables, encoding='utf8', debug=False):
    """Set connection for every table."""
    kw = {}
    # FIXME: it's absolutely unclear what we should do to correctly
    #        support unicode in MySQL; with some versions of SQLObject,
    #        it seems that setting use_unicode=1 is the _wrong_ thing to do.
    _uriLower = uri.lower()
    if _uriLower.startswith('mysql'):
        kw['use_unicode'] = 1
        #kw['sqlobject_encoding'] = encoding
        kw['charset'] = encoding
    conn = connectionForURI(uri, **kw)
    conn.debug = debug
    if uri.startswith('sqlite'):
        major = sys.version_info[0]
        minor = sys.version_info[1]
        if major > 2 or (major == 2 and minor > 5):
            conn.connection.connection.text_factory = str
    for table in tables:
        table.setConnection(conn)
        #table.sqlmeta.cacheValues = False
        # FIXME: is it safe to set table._cacheValue to False?  Looks like
        #        we can't retrieve correct values after an update (I think
        #        it's never needed, but...)  Anyway, these are set to False
        #        for performance reason at insert time (see imdbpy2sql.py).
        table._cacheValue = False
    # Required by imdbpy2sql.py.
    conn.paramstyle = conn.module.paramstyle
    return conn

