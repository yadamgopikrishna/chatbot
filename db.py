import os
import sys

# Ensure UTF-8 Oracle Client encoding
os.environ["NLS_LANG"] = "AMERICAN_AMERICA.AL32UTF8"
os.environ["PYTHONIOENCODING"] = "utf-8"

import sqlite3
import logging
from contextlib import contextmanager
from config import (
    ORACLE_CLIENT_DIR,
    ORACLE_USER,
    ORACLE_PASSWORD,
    ORACLE_DSN,
    SQLITE_DB_PATH,
    DB_TYPE
)

logger = logging.getLogger(__name__)

_oracle_initialized = False
_using_oracle = False

# Try initializing Oracle client in thick mode
try:
    import oracledb
    if ORACLE_CLIENT_DIR and os.path.exists(ORACLE_CLIENT_DIR):
        try:
            oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_DIR)
            _oracle_initialized = True
            logger.info("Oracle Instant Client initialized from: %s", ORACLE_CLIENT_DIR)
        except Exception as e:
            _oracle_initialized = True
            logger.warning("Oracle Instant Client note: %s", e)
    else:
        logger.warning("Oracle Instant Client path not found, will attempt thin/sqlite fallback")
except Exception as e:
    logger.warning("oracledb module or client init issue: %s", e)


def get_connection():
    """
    Returns an active database connection.
    Prioritizes Oracle Database 11g XE in Thick Mode, gracefully falls back to SQLite.
    """
    global _using_oracle
    if DB_TYPE == "oracle" or _oracle_initialized:
        try:
            import oracledb
            conn = oracledb.connect(
                user=ORACLE_USER,
                password=ORACLE_PASSWORD,
                dsn=ORACLE_DSN
            )
            _using_oracle = True
            return conn
        except Exception as e:
            logger.warning("Oracle XE connection failed (%s), falling back to SQLite", e)
            _using_oracle = False

    # SQLite fallback
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _using_oracle = False
    return conn


def is_oracle():
    """Returns True if connected to Oracle Database."""
    return _using_oracle


@contextmanager
def db_cursor(commit=False):
    """Context manager for obtaining a database cursor and auto-committing/closing."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor, conn
        if commit:
            conn.commit()
    except Exception as e:
        if commit:
            conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def execute_sql(sql_oracle, sql_sqlite, params=(), fetch_one=False, fetch_all=False, commit=False):
    """
    Helper to execute dialect-appropriate SQL across Oracle and SQLite.
    """
    conn = get_connection()
    is_ora = not isinstance(conn, sqlite3.Connection)
    sql = sql_oracle if is_ora else sql_sqlite
    
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        if commit:
            conn.commit()
        if fetch_one:
            res = cursor.fetchone()
            if res and isinstance(conn, sqlite3.Connection):
                return dict(res)
            return res
        if fetch_all:
            res = cursor.fetchall()
            if res and isinstance(conn, sqlite3.Connection):
                return [dict(r) for r in res]
            return res
        return cursor.rowcount
    finally:
        cursor.close()
        conn.close()
