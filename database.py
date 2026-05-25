"""
Banco de dados local do cliente — SQLite.
Persiste histórico de conversas e lista de contatos.
"""
from __future__ import annotations

import sqlite3
import threading

DB_PATH = "chat_client.db"
_conn   = None       # sqlite3.Connection
_lock   = threading.Lock()


def init_db():
    global _conn
    _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            me        TEXT NOT NULL,
            contact   TEXT NOT NULL,
            sender    TEXT NOT NULL,
            text      TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_conv ON messages(me, contact);

        CREATE TABLE IF NOT EXISTS contacts (
            username TEXT PRIMARY KEY,
            status   TEXT DEFAULT 'offline'
        );
    """)
    _conn.commit()


def save_message(me: str, contact: str, sender: str,
                 text: str, timestamp: str):
    with _lock:
        _conn.execute(
            "INSERT INTO messages (me,contact,sender,text,timestamp) "
            "VALUES (?,?,?,?,?)",
            (me, contact, sender, text, timestamp)
        )
        _conn.commit()


def get_history(me: str, contact: str) -> list:
    with _lock:
        rows = _conn.execute(
            "SELECT sender, text, timestamp FROM messages "
            "WHERE me=? AND contact=? ORDER BY id",
            (me, contact)
        ).fetchall()
    return [{"sender": r["sender"], "text": r["text"],
             "timestamp": r["timestamp"]} for r in rows]


def save_contacts(contacts: list):
    with _lock:
        for c in contacts:
            _conn.execute(
                "INSERT INTO contacts (username, status) VALUES (?,?) "
                "ON CONFLICT(username) DO UPDATE SET status=excluded.status",
                (c["username"], c.get("status", "offline"))
            )
        _conn.commit()


def update_contact_status(username: str, status: str):
    with _lock:
        _conn.execute(
            "INSERT INTO contacts (username, status) VALUES (?,?) "
            "ON CONFLICT(username) DO UPDATE SET status=excluded.status",
            (username, status)
        )
        _conn.commit()


def get_contacts() -> list:
    with _lock:
        rows = _conn.execute(
            "SELECT username, status FROM contacts ORDER BY username"
        ).fetchall()
    return [{"username": r["username"], "status": r["status"]} for r in rows]
