"""
Use clara_database_adapter to make code work for both sqlite3 and PostgreSQL databases.

The type of database is set in the DB_TYPE environment variable.
This should be 'sqlite' for 'sqlite3' databases. Default is PostgreSQL.

SQL templates must be written in PostgreSQL format with %s signifying a parameter placeholder.
The function clara_database_adapter.localise_sql_query converts this to sqlite3 format
(i.e. ? for a placeholder) if DB_TYPE is sqlite.
"""

import os
import urllib.parse as urlparse
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

from .clara_utils import get_config

config = get_config()

def connect(database_name):
    if os.getenv('DB_TYPE') == 'sqlite':
        return sqlite3.connect(database_name)
    else:  # Assuming PostgreSQL on Heroku
        url = urlparse.urlparse(os.environ.get('DATABASE_URL'))
        dbname = url.path[1:]
        user = url.username
        password = url.password
        host = url.hostname
        return psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            cursor_factory=RealDictCursor
        )

def localise_sql_query(query):
    if os.getenv('DB_TYPE') == 'sqlite':
        query = query.replace('%s', '?')
    else:  # Assuming PostgreSQL
        # The query is already in PostgreSQL format
        pass
    return query
