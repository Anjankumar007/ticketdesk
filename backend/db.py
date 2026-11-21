"""db.py - the only file that knows how to talk to MySQL."""
import os
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
import mysql.connector
from dotenv import load_dotenv

load_dotenv()   # reads DB_PASSWORD etc. from a .env file (never committed to GitHub)

# Credentials come from the .env file (copy .env.example to .env). Never hard-code them here.
if os.environ.get("DB_PASSWORD") is None:
    raise RuntimeError("DB_PASSWORD is not set. Copy .env.example to .env and put your MySQL password in it.")

CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ["DB_PASSWORD"],
    "database": "ticketdesk",
}


def connect():
    return mysql.connector.connect(**CONFIG)


def clean(v):
    """MySQL types that JSON cannot carry -> plain numbers / text."""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return str(v)
    return v


def query(sql, params=(), as_dict=True):
    """Run a SELECT and return all rows."""
    conn = connect()
    try:
        cur = conn.cursor(dictionary=as_dict)
        cur.execute(sql, params)
        rows = cur.fetchall()
        if as_dict:
            return [{k: clean(v) for k, v in r.items()} for r in rows]
        return [[clean(v) for v in r] for r in rows]
    finally:
        conn.close()


@contextmanager
def transaction():
    """Several statements, all-or-nothing: COMMIT if no error, ROLLBACK if any."""
    conn = connect()
    try:
        cur = conn.cursor(dictionary=True)
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
