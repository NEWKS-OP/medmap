import sqlite3
import os
from config.settings import DB_PATH, DATA_DIR

_conn = None


def get_db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        db_full_path = os.path.join(DATA_DIR, "..", DB_PATH) if not os.path.isabs(DB_PATH) else DB_PATH
        db_full_path = os.path.normpath(db_full_path)
        os.makedirs(os.path.dirname(db_full_path), exist_ok=True)
        _conn = sqlite3.connect(db_full_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def close_db():
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
