# people and access log
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Resident',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time TEXT NOT NULL,
    kind TEXT NOT NULL,           -- granted, denied or remote
    person_id INTEGER,
    name TEXT NOT NULL,
    distance REAL,
    snapshot TEXT
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init():
    config.ensure_folders()
    with connect() as conn:
        conn.executescript(SCHEMA)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_person(name, role):
    with connect() as conn:
        cur = conn.execute("INSERT INTO people (name, role, created_at) VALUES (?, ?, ?)", (name, role, now()))
        return cur.lastrowid


def people():
    with connect() as conn:
        rows = conn.execute("""SELECT p.*, (SELECT MAX(time) FROM events e WHERE e.person_id = p.id AND e.kind = 'granted') AS last_seen
                               FROM people p ORDER BY p.name""").fetchall()
    return [dict(r) for r in rows]


def person(person_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
    return dict(row) if row else None


def delete_person(person_id):
    with connect() as conn:
        conn.execute("DELETE FROM people WHERE id = ?", (person_id,))


def log_event(kind, name, person_id=None, distance=None, snapshot=None):
    with connect() as conn:
        conn.execute("INSERT INTO events (time, kind, person_id, name, distance, snapshot) VALUES (?, ?, ?, ?, ?, ?)",
                     (now(), kind, person_id, name, distance, snapshot))


def events(kind=None, limit=200):
    sql, args = "SELECT * FROM events", []
    if kind:
        sql += " WHERE kind = ?"
        args.append(kind)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def today_counts():
    day = datetime.now().strftime("%Y-%m-%d")
    with connect() as conn:
        rows = conn.execute("SELECT kind, COUNT(*) AS n FROM events WHERE time LIKE ? GROUP BY kind", (day + "%",)).fetchall()
    counts = {"granted": 0, "denied": 0, "remote": 0}
    counts.update({r["kind"]: r["n"] for r in rows})
    return counts
