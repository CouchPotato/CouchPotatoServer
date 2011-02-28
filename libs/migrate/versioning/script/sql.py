#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import shutil

from migrate.versioning.script import base
from migrate.versioning.template import Template


log = logging.getLogger(__name__)

class SqlScript(base.BaseScript):
    """A file containing plain SQL statements."""

    @classmethod
    def create(cls, path, **opts):
        """Create an empty migration script at specified path
        
        :returns: :class:`SqlScript instance <migrate.versioning.script.sql.SqlScript>`"""
        cls.require_notfound(path)

        src = Template(opts.pop('templates_path', None)).get_sql_script(theme=opts.pop('templates_theme', None))
        shutil.copy(src, path)
        return cls(path)

    # TODO: why is step parameter even here?
    def run(self, engine, step=None, executemany=True):
        """Runs SQL script through raw dbapi execute call"""
        text = self.source()
        # Don't rely on SA's autocommit here
        # (SA uses .startswith to check if a commit is needed. What if script
        # starts with a comment?)
        conn = engine.connect()
        try:
            trans = conn.begin()
            try:
                # HACK: SQLite doesn't allow multiple statements through
                # its execute() method, but it provides executescript() instead
                dbapi = conn.engine.raw_connection()
                if executemany and getattr(dbapi, 'executescript', None):
                    dbapi.executescript(text)
                else:
                    conn.execute(text)
                trans.commit()
            except:
                trans.rollback()
                raise
        finally:
            conn.close()
