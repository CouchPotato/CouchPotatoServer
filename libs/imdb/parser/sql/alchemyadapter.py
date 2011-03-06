"""
parser.sql.alchemyadapter module (imdb.parser.sql package).

This module adapts the SQLAlchemy ORM to the internal mechanism.

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

import re
import sys
import logging
from sqlalchemy import *
from sqlalchemy import schema
try: from sqlalchemy import exc # 0.5
except ImportError: from sqlalchemy import exceptions as exc # 0.4

_alchemy_logger = logging.getLogger('imdbpy.parser.sql.alchemy')

try:
    import migrate.changeset
    HAS_MC = True
except ImportError:
    HAS_MC = False
    _alchemy_logger.warn('Unable to import migrate.changeset: Foreign ' \
                         'Keys will not be created.')

from imdb._exceptions import IMDbDataAccessError
from dbschema import *

# Used to convert table and column names.
re_upper = re.compile(r'([A-Z])')

# XXX: I'm not sure at all that this is the best method to connect
#      to the database and bind that connection to every table.
metadata = MetaData()

# Maps our placeholders to SQLAlchemy's column types.
MAP_COLS = {
    INTCOL: Integer,
    UNICODECOL: UnicodeText,
    STRINGCOL: String
}


class NotFoundError(IMDbDataAccessError):
    """Exception raised when Table.get(id) returns no value."""
    pass


def _renameTable(tname):
    """Build the name of a table, as done by SQLObject."""
    tname = re_upper.sub(r'_\1', tname)
    if tname.startswith('_'):
        tname = tname[1:]
    return tname.lower()

def _renameColumn(cname):
    """Build the name of a column, as done by SQLObject."""
    cname = cname.replace('ID', 'Id')
    return _renameTable(cname)


class DNNameObj(object):
    """Used to access table.sqlmeta.columns[column].dbName (a string)."""
    def __init__(self, dbName):
        self.dbName = dbName

    def __repr__(self):
        return '<DNNameObj(dbName=%s) [id=%s]>' % (self.dbName, id(self))


class DNNameDict(object):
    """Used to access table.sqlmeta.columns (a dictionary)."""
    def __init__(self, colMap):
        self.colMap = colMap

    def __getitem__(self, key):
        return DNNameObj(self.colMap[key])

    def __repr__(self):
        return '<DNNameDict(colMap=%s) [id=%s]>' % (self.colMap, id(self))


class SQLMetaAdapter(object):
    """Used to access table.sqlmeta (an object with .table, .columns and
    .idName attributes)."""
    def __init__(self, table, colMap=None):
        self.table = table
        if colMap is None:
            colMap = {}
        self.colMap = colMap

    def __getattr__(self, name):
        if name == 'table':
            return getattr(self.table, name)
        if name == 'columns':
            return DNNameDict(self.colMap)
        if name == 'idName':
            return self.colMap.get('id', 'id')
        return None

    def __repr__(self):
        return '<SQLMetaAdapter(table=%s, colMap=%s) [id=%s]>' % \
                (repr(self.table), repr(self.colMap), id(self))


class QAdapter(object):
    """Used to access table.q attribute (remapped to SQLAlchemy table.c)."""
    def __init__(self, table, colMap=None):
        self.table = table
        if colMap is None:
            colMap = {}
        self.colMap = colMap

    def __getattr__(self, name):
        try: return getattr(self.table.c, self.colMap[name])
        except KeyError, e: raise AttributeError, "unable to get '%s'" % name

    def __repr__(self):
        return '<QAdapter(table=%s, colMap=%s) [id=%s]>' % \
                (repr(self.table), repr(self.colMap), id(self))


class RowAdapter(object):
    """Adapter for a SQLAlchemy RowProxy object."""
    def __init__(self, row, table, colMap=None):
        self.row = row
        # FIXME: it's OBSCENE that 'table' should be passed from
        #        TableAdapter through ResultAdapter only to land here,
        #        where it's used to directly update a row item.
        self.table = table
        if colMap is None:
            colMap = {}
        self.colMap = colMap
        self.colMapKeys = colMap.keys()

    def __getattr__(self, name):
        try: return getattr(self.row, self.colMap[name])
        except KeyError, e: raise AttributeError, "unable to get '%s'" % name

    def __setattr__(self, name, value):
        # FIXME: I can't even think about how much performances suffer,
        #        for this horrible hack (and it's used so rarely...)
        #        For sure something like a "property" to map column names
        #        to getter/setter functions would be much better, but it's
        #        not possible (or at least not easy) to build them for a
        #        single instance.
        if name in self.__dict__.get('colMapKeys', ()):
            # Trying to update a value in the database.
            row = self.__dict__['row']
            table = self.__dict__['table']
            colMap = self.__dict__['colMap']
            params = {colMap[name]: value}
            table.update(table.c.id==row.id).execute(**params)
            # XXX: minor bug: after a value is assigned with the
            #      'rowAdapterInstance.colName = value' syntax, for some
            #      reason rowAdapterInstance.colName still returns the
            #      previous value (even if the database is updated).
            #      Fix it?  I'm not even sure it's ever used.
            return
        # For every other attribute.
        object.__setattr__(self, name, value)

    def __repr__(self):
        return '<RowAdapter(row=%s, table=%s, colMap=%s) [id=%s]>' % \
                (repr(self.row), repr(self.table), repr(self.colMap), id(self))


class ResultAdapter(object):
    """Adapter for a SQLAlchemy ResultProxy object."""
    def __init__(self, result, table, colMap=None):
        self.result = result
        self.table = table
        if colMap is None:
            colMap = {}
        self.colMap = colMap

    def count(self):
        return len(self)

    def __len__(self):
        # FIXME: why sqlite returns -1? (that's wrooong!)
        if self.result.rowcount == -1:
            return 0
        return self.result.rowcount

    def __getitem__(self, key):
        res = list(self.result)[key]
        if not isinstance(key, slice):
            # A single item.
            return RowAdapter(res, self.table, colMap=self.colMap)
        else:
            # A (possible empty) list of items.
            return [RowAdapter(x, self.table, colMap=self.colMap)
                    for x in res]

    def __iter__(self):
        for item in self.result:
            yield RowAdapter(item, self.table, colMap=self.colMap)

    def __repr__(self):
        return '<ResultAdapter(result=%s, table=%s, colMap=%s) [id=%s]>' % \
                (repr(self.result), repr(self.table),
                    repr(self.colMap), id(self))


class TableAdapter(object):
    """Adapter for a SQLAlchemy Table object, to mimic a SQLObject class."""
    def __init__(self, table, uri=None):
        """Initialize a TableAdapter object."""
        self._imdbpySchema = table
        self._imdbpyName = table.name
        self.connectionURI = uri
        self.colMap = {}
        columns = []
        for col in table.cols:
            # Column's paramters.
            params = {'nullable': True}
            params.update(col.params)
            if col.name == 'id':
                params['primary_key'] = True
            if 'notNone' in params:
                params['nullable'] = not params['notNone']
                del params['notNone']
            cname = _renameColumn(col.name)
            self.colMap[col.name] = cname
            colClass = MAP_COLS[col.kind]
            colKindParams = {}
            if 'length' in params:
                colKindParams['length'] = params['length']
                del params['length']
            elif colClass is UnicodeText and col.index:
                # XXX: limit length for UNICODECOLs that will have an index.
                #      this can result in name.name and title.title truncations!
                colClass = Unicode
                # Should work for most of the database servers.
                length = 511
                if self.connectionURI:
                    if self.connectionURI.startswith('mysql'):
                        # To stay compatible with MySQL 4.x.
                        length = 255
                colKindParams['length'] = length
            elif self._imdbpyName == 'PersonInfo' and col.name == 'info':
                if self.connectionURI:
                    if self.connectionURI.startswith('ibm'):
                        # There are some entries longer than 32KB.
                        colClass = CLOB
                        # I really do hope that this space isn't wasted
                        # for each other shorter entry... <g>
                        colKindParams['length'] = 68*1024
            colKind = colClass(**colKindParams)
            if 'alternateID' in params:
                # There's no need to handle them here.
                del params['alternateID']
            # Create a column.
            colObj = Column(cname, colKind, **params)
            columns.append(colObj)
        self.tableName = _renameTable(table.name)
        # Create the table.
        self.table = Table(self.tableName, metadata, *columns)
        self._ta_insert = self.table.insert()
        self._ta_select = self.table.select
        # Adapters for special attributes.
        self.q = QAdapter(self.table, colMap=self.colMap)
        self.sqlmeta = SQLMetaAdapter(self.table, colMap=self.colMap)

    def select(self, conditions=None):
        """Return a list of results."""
        result = self._ta_select(conditions).execute()
        return ResultAdapter(result, self.table, colMap=self.colMap)

    def get(self, theID):
        """Get an object given its ID."""
        result = self.select(self.table.c.id == theID)
        #if not result:
        #    raise NotFoundError, 'no data for ID %s' % theID
        # FIXME: isn't this a bit risky?  We can't check len(result),
        #        because sqlite returns -1...
        #        What about converting it to a list and getting the first item?
        try:
            return result[0]
        except KeyError:
            raise NotFoundError, 'no data for ID %s' % theID

    def dropTable(self, checkfirst=True):
        """Drop the table."""
        dropParams = {'checkfirst': checkfirst}
        # Guess what?  Another work-around for a ibm_db bug.
        if self.table.bind.engine.url.drivername.startswith('ibm_db'):
            del dropParams['checkfirst']
        try:
            self.table.drop(**dropParams)
        except exc.ProgrammingError:
            # As above: re-raise the exception, but only if it's not ibm_db.
            if not self.table.bind.engine.url.drivername.startswith('ibm_db'):
                raise

    def createTable(self, checkfirst=True):
        """Create the table."""
        self.table.create(checkfirst=checkfirst)
        # Create indexes for alternateID columns (other indexes will be
        # created later, at explicit request for performances reasons).
        for col in self._imdbpySchema.cols:
            if col.name == 'id':
                continue
            if col.params.get('alternateID', False):
                self._createIndex(col, checkfirst=checkfirst)

    def _createIndex(self, col, checkfirst=True):
        """Create an index for a given (schema) column."""
        # XXX: indexLen is ignored in SQLAlchemy, and that means that
        #      indexes will be over the whole 255 chars strings...
        # NOTE: don't use a dot as a separator, or DB2 will do
        #       nasty things.
        idx_name = '%s_%s' % (self.table.name, col.index or col.name)
        if checkfirst:
            for index in self.table.indexes:
                if index.name == idx_name:
                    return
        idx = Index(idx_name, getattr(self.table.c, self.colMap[col.name]))
        # XXX: beware that exc.OperationalError can be raised, is some
        #      strange circumstances; that's why the index name doesn't
        #      follow the SQLObject convention, but includes the table name:
        #      sqlite, for example, expects index names to be unique at
        #      db-level.
        try:
            idx.create()
        except exc.OperationalError, e:
            _alchemy_logger.warn('Skipping creation of the %s.%s index: %s' %
                                (self.sqlmeta.table, col.name, e))

    def addIndexes(self, ifNotExists=True):
        """Create all required indexes."""
        for col in self._imdbpySchema.cols:
            if col.index:
                self._createIndex(col, checkfirst=ifNotExists)

    def addForeignKeys(self, mapTables, ifNotExists=True):
        """Create all required foreign keys."""
        if not HAS_MC:
            return
        # It seems that there's no reason to prevent the creation of
        # indexes for columns with FK constrains: if there's already
        # an index, the FK index is not created.
        countCols = 0
        for col in self._imdbpySchema.cols:
            countCols += 1
            if not col.foreignKey:
                continue
            fks = col.foreignKey.split('.', 1)
            foreignTableName = fks[0]
            if len(fks) == 2:
                foreignColName = fks[1]
            else:
                foreignColName = 'id'
            foreignColName = mapTables[foreignTableName].colMap.get(
                                                foreignColName, foreignColName)
            thisColName = self.colMap.get(col.name, col.name)
            thisCol = self.table.columns[thisColName]
            foreignTable = mapTables[foreignTableName].table
            foreignCol = getattr(foreignTable.c, foreignColName)
            # Need to explicitly set an unique name, otherwise it will
            # explode, if two cols points to the same table.
            fkName = 'fk_%s_%s_%d' % (foreignTable.name, foreignColName,
                                        countCols)
            constrain = migrate.changeset.ForeignKeyConstraint([thisCol],
                                                        [foreignCol],
                                                        name=fkName)
            try:
                constrain.create()
            except exc.OperationalError:
                continue

    def __call__(self, *args, **kwds):
        """To insert a new row with the syntax: TableClass(key=value, ...)"""
        taArgs = {}
        for key, value in kwds.items():
            taArgs[self.colMap.get(key, key)] = value
        self._ta_insert.execute(*args, **taArgs)

    def __repr__(self):
        return '<TableAdapter(table=%s) [id=%s]>' % (repr(self.table), id(self))


# Module-level "cache" for SQLObject classes, to prevent
# "Table 'tableName' is already defined for this MetaData instance" errors,
# when two or more connections to the database are made.
# XXX: is this the best way to act?
TABLES_REPOSITORY = {}

def getDBTables(uri=None):
    """Return a list of TableAdapter objects to be used to access the
    database through the SQLAlchemy ORM.  The connection uri is optional, and
    can be used to tailor the db schema to specific needs."""
    DB_TABLES = []
    for table in DB_SCHEMA:
        if table.name in TABLES_REPOSITORY:
            DB_TABLES.append(TABLES_REPOSITORY[table.name])
            continue
        tableAdapter = TableAdapter(table, uri)
        DB_TABLES.append(tableAdapter)
        TABLES_REPOSITORY[table.name] = tableAdapter
    return DB_TABLES


# Functions used to emulate SQLObject's logical operators.
def AND(*params):
    """Emulate SQLObject's AND."""
    return and_(*params)

def OR(*params):
    """Emulate SQLObject's OR."""
    return or_(*params)

def IN(item, inList):
    """Emulate SQLObject's IN."""
    if not isinstance(item, schema.Column):
        return OR(*[x == item for x in inList])
    else:
        return item.in_(inList)

def ISNULL(x):
    """Emulate SQLObject's ISNULL."""
    # XXX: Should we use null()?  Can null() be a global instance?
    # XXX: Is it safe to test None with the == operator, in this case?
    return x == None

def ISNOTNULL(x):
    """Emulate SQLObject's ISNOTNULL."""
    return x != None

def CONTAINSSTRING(expr, pattern):
    """Emulate SQLObject's CONTAINSSTRING."""
    return expr.like('%%%s%%' % pattern)


def toUTF8(s):
    """For some strange reason, sometimes SQLObject wants utf8 strings
    instead of unicode; with SQLAlchemy we just return the unicode text."""
    return s


class _AlchemyConnection(object):
    """A proxy for the connection object, required since _ConnectionFairy
    uses __slots__."""
    def __init__(self, conn):
        self.conn = conn

    def __getattr__(self, name):
        return getattr(self.conn, name)


def setConnection(uri, tables, encoding='utf8', debug=False):
    """Set connection for every table."""
    # FIXME: why on earth MySQL requires an additional parameter,
    #        is well beyond my understanding...
    if uri.startswith('mysql'):
        if '?' in uri:
            uri += '&'
        else:
            uri += '?'
        uri += 'charset=%s' % encoding
    params = {'encoding': encoding}
    if debug:
        params['echo'] = True
    if uri.startswith('ibm_db'):
        # Try to work-around a possible bug of the ibm_db DB2 driver.
        params['convert_unicode'] = True
    # XXX: is this the best way to connect?
    engine = create_engine(uri, **params)
    metadata.bind = engine
    eng_conn = engine.connect()
    if uri.startswith('sqlite'):
        major = sys.version_info[0]
        minor = sys.version_info[1]
        if major > 2 or (major == 2 and minor > 5):
            eng_conn.connection.connection.text_factory = str
    # XXX: OH MY, THAT'S A MESS!
    #      We need to return a "connection" object, with the .dbName
    #      attribute set to the db engine name (e.g. "mysql"), .paramstyle
    #      set to the style of the paramters for query() calls, and the
    #      .module attribute set to a module (?) with .OperationalError and
    #      .IntegrityError attributes.
    #      Another attribute of "connection" is the getConnection() function,
    #      used to return an object with a .cursor() method.
    connection = _AlchemyConnection(eng_conn.connection)
    paramstyle = eng_conn.dialect.paramstyle
    connection.module = eng_conn.dialect.dbapi
    connection.paramstyle = paramstyle
    connection.getConnection = lambda: connection.connection
    connection.dbName = engine.url.drivername
    return connection


