"""
SessionManager — controla quais usuários estão online, thread-safe.
"""
from __future__ import annotations

import threading
import protocol as P


class SessionManager:
    def __init__(self):
        self._lock     = threading.Lock()
        self._sessions = {}   # dict[str, ClientHandler]

    def register_session(self, username: str, handler):
        with self._lock:
            self._sessions[username] = handler

    def remove_session(self, username: str):
        with self._lock:
            self._sessions.pop(username, None)

    def get_handler(self, username: str):
        with self._lock:
            return self._sessions.get(username)

    def online_users(self) -> set:
        with self._lock:
            return set(self._sessions.keys())

    def broadcast_status(self, username: str, status: str, exclude: str = None):
        """Notifica todos os clientes online sobre mudança de status."""
        pkt = {"type": P.MSG_STATUS_UPDATE,
               "username": username, "status": status}
        with self._lock:
            targets = [(u, h) for u, h in self._sessions.items()
                       if u != exclude]
        for _, handler in targets:
            handler.send(pkt)
