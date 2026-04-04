import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "scout.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT DEFAULT '',
            estimated_price REAL DEFAULT 0,
            added_date TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            purchased_date TEXT,
            notes TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            year_month TEXT NOT NULL,
            budget_limit REAL NOT NULL,
            UNIQUE(user, year_month)
        );
    """)
    conn.close()
