"""SQLite data layer for Spendly.

Establishes the schema, seed data, and a per-request connection helper
used by every later step (auth, expenses, etc.).
"""

import os
import sqlite3
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

# Resolve the DB file to the project root (one level above this package),
# regardless of the current working directory.
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spendly.db")

# Fixed list of expense categories (spec §10). Do not rename.
CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


def get_db():
    """Open and return a SQLite connection for the Spendly database.

    Configures:
        - row_factory = sqlite3.Row  (dict-like column access)
        - PRAGMA foreign_keys = ON   (enforces REFERENCES)
    Callers own the connection lifecycle (close it when done).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the schema. Safe to call on every startup."""
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );
            """
        )


def seed_db():
    """Insert demo data exactly once.

    Only seeds if the ``users`` table is empty; on every later call it
    returns early, so repeated runs never duplicate data.
    """
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        if count > 0:
            return  # already seeded — do not duplicate

        # One demo user, password stored as a hash.
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        demo_user_id = cur.lastrowid

        # 8 sample expenses; every category appears at least once (Food twice).
        today = date.today()
        sample_expenses = [
            ("Food", 12.50, "Lunch at the canteen"),
            ("Transport", 3.25, "Bus fare"),
            ("Bills", 85.00, "Electricity"),
            ("Health", 24.00, "Pharmacy"),
            ("Entertainment", 15.00, "Cinema ticket"),
            ("Shopping", 49.99, "New headphones"),
            ("Other", 8.75, None),
            ("Food", 6.40, "Coffee and pastry"),
        ]
        # Spread the spend dates across the current month (newest first).
        days = [today - timedelta(days=n) for n in range(7, -1, -1)]
        for (category, amount, description), when in zip(sample_expenses, days):
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description)"
                " VALUES (?, ?, ?, ?, ?)",
                (demo_user_id, amount, category, when.isoformat(), description),
            )

        conn.commit()