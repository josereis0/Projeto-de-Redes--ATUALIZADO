"""
Camada de persistência do servidor — SQLite com WAL mode.
Cada thread usa sua própria conexão via threading.local().
"""
from __future__ import annotations

import sqlite3
import hashlib
import threading
from datetime import datetime

DB_PATH = "chat_server.db"
_local  = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


def init_db():
    """Inicializa o schema. Chame uma vez na startup do servidor."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username   TEXT PRIMARY KEY,
            password   TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS offline_messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            sender    TEXT NOT NULL,
            recipient TEXT NOT NULL,
            text      TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    print("[DB] Banco de dados inicializado.")


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ── Usuários ──────────────────────────────────────────────────────────────────

def register_user(username: str, password: str) -> bool:
    """Registra novo usuário. Retorna False se nome já existe."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password, created_at) VALUES (?,?,?)",
            (username, _hash(password), datetime.utcnow().isoformat())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def authenticate(username: str, password: str) -> bool:
    """Retorna True se username e password conferem."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT password FROM users WHERE username=?", (username,)
    ).fetchone()
    return bool(row and row["password"] == _hash(password))


def get_all_usernames() -> list:
    """Retorna lista de todos os usuários cadastrados."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT username FROM users ORDER BY username"
    ).fetchall()
    return [r["username"] for r in rows]


# ── Mensagens offline ─────────────────────────────────────────────────────────

def store_offline_message(sender: str, recipient: str,
                          text: str, timestamp: str):
    """Armazena mensagem para entrega quando destinatário conectar."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO offline_messages (sender, recipient, text, timestamp) "
        "VALUES (?,?,?,?)",
        (sender, recipient, text, timestamp)
    )
    conn.commit()


def fetch_and_clear_offline(recipient: str) -> list:
    """Busca e remove todas as mensagens offline de recipient."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, sender, text, timestamp FROM offline_messages "
        "WHERE recipient=? ORDER BY id",
        (recipient,)
    ).fetchall()
    if rows:
        ids = [r["id"] for r in rows]
        conn.execute(
            "DELETE FROM offline_messages WHERE id IN ({})".format(
                ",".join("?" * len(ids))),
            ids
        )
        conn.commit()
    return [
        {"from": r["sender"], "text": r["text"], "timestamp": r["timestamp"]}
        for r in rows
    ]
