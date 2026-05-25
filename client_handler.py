"""
ClientHandler — uma thread por cliente conectado.
"""
from __future__ import annotations

import socket
import threading
import logging
from datetime import datetime

import protocol as P
import database as DB

logger = logging.getLogger("handler")


class ClientHandler(threading.Thread):
    def __init__(self, sock: socket.socket, addr, session_manager):
        super().__init__(daemon=True)
        self.sock     = sock
        self.addr     = addr
        self.sm       = session_manager
        self.username = None
        self._buffer  = ""
        self._send_lock = threading.Lock()

    # ── I/O ──────────────────────────────────────────────────────────────────

    def send(self, packet: dict):
        """Thread-safe: vários threads podem chamar simultaneamente."""
        data = P.encode(packet)
        with self._send_lock:
            try:
                self.sock.sendall(data)
            except OSError:
                pass

    def _recv_line(self):
        while "\n" not in self._buffer:
            try:
                chunk = self.sock.recv(4096)
            except OSError:
                return None
            if not chunk:
                return None
            self._buffer += chunk.decode("utf-8", errors="replace")
        line, self._buffer = self._buffer.split("\n", 1)
        return line.strip()

    # ── Loop principal ────────────────────────────────────────────────────────

    def run(self):
        logger.info("Conexão: %s", self.addr)
        try:
            while True:
                line = self._recv_line()
                if line is None:
                    break
                if not line:
                    continue
                try:
                    pkt = P.decode(line)
                except Exception as e:
                    logger.warning("Pacote inválido de %s: %s", self.addr, e)
                    continue
                self._dispatch(pkt)
        finally:
            self._disconnect()

    def _dispatch(self, pkt: dict):
        t = pkt.get("type")
        if   t == P.MSG_REGISTER:    self._on_register(pkt)
        elif t == P.MSG_LOGIN:        self._on_login(pkt)
        elif t == P.MSG_LOGOUT:       self._disconnect()
        elif t == P.MSG_SEND:         self._on_message(pkt)
        elif t == P.MSG_TYPING_START: self._on_typing(pkt, started=True)
        elif t == P.MSG_TYPING_STOP:  self._on_typing(pkt, started=False)
        elif t == P.MSG_GET_CONTACTS: self._on_get_contacts()

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _on_register(self, pkt):
        username = pkt.get("username", "").strip()
        password = pkt.get("password", "")
        if not username or not password:
            self.send({"type": P.MSG_REGISTER_FAIL, "reason": "Campos inválidos."})
            return
        if not (2 <= len(username) <= 32):
            self.send({"type": P.MSG_REGISTER_FAIL,
                       "reason": "Usuário deve ter entre 2 e 32 caracteres."})
            return
        if DB.register_user(username, password):
            logger.info("Registrado: %s", username)
            self.send({"type": P.MSG_REGISTER_OK})
        else:
            self.send({"type": P.MSG_REGISTER_FAIL,
                       "reason": "Nome de usuário já existe."})

    def _on_login(self, pkt):
        username = pkt.get("username", "").strip()
        password = pkt.get("password", "")

        if not DB.authenticate(username, password):
            self.send({"type": P.MSG_LOGIN_FAIL,
                       "reason": "Usuário ou senha inválidos."})
            return

        # ── FIX race condition ────────────────────────────────────────────────
        # Antes de registrar a nova sessão, invalida o username do handler antigo.
        # Sem isso, o _disconnect() do handler antigo removeria a NOVA sessão.
        old = self.sm.get_handler(username)
        if old and old is not self:
            old.username = None          # invalida antes de fechar
            try:
                old.sock.close()
            except OSError:
                pass
        # ─────────────────────────────────────────────────────────────────────

        self.username = username
        self.sm.register_session(username, self)
        logger.info("Login: %s (%s)", username, self.addr)

        # notifica peers sobre novo online
        self.sm.broadcast_status(username, "online", exclude=username)

        self.send({
            "type":     P.MSG_LOGIN_OK,
            "username": username,
            "contacts": self._build_contacts_list(),
        })

        # entrega mensagens offline acumuladas
        offline = DB.fetch_and_clear_offline(username)
        if offline:
            self.send({"type": P.MSG_OFFLINE_BATCH, "messages": offline})

    def _on_message(self, pkt):
        if not self.username:
            return
        recipient = pkt.get("to", "").strip()
        text      = pkt.get("text", "").strip()
        timestamp = pkt.get("timestamp") or datetime.utcnow().isoformat()
        if not recipient or not text:
            return

        delivery = {
            "type":      P.MSG_DELIVER,
            "from":      self.username,
            "text":      text,
            "timestamp": timestamp,
        }
        target = self.sm.get_handler(recipient)
        if target:
            target.send(delivery)
        else:
            DB.store_offline_message(self.username, recipient, text, timestamp)

    def _on_typing(self, pkt, started: bool):
        if not self.username:
            return
        recipient = pkt.get("to", "").strip()
        target    = self.sm.get_handler(recipient)
        if target:
            t = P.MSG_TYPING_IND if started else P.MSG_TYPING_STOP_IND
            target.send({"type": t, "from": self.username})

    def _on_get_contacts(self):
        if not self.username:
            return
        self.send({"type": P.MSG_CONTACTS_LIST,
                   "contacts": self._build_contacts_list()})

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_contacts_list(self) -> list:
        all_users = DB.get_all_usernames()
        online    = self.sm.online_users()
        return [
            {"username": u, "status": "online" if u in online else "offline"}
            for u in all_users
            if u != self.username
        ]

    def _disconnect(self):
        username = self.username
        if username:
            self.username = None
            # só remove da sessão se este handler ainda é o ativo
            if self.sm.get_handler(username) is self:
                self.sm.remove_session(username)
                self.sm.broadcast_status(username, "offline")
                logger.info("Offline: %s", username)
        try:
            self.sock.close()
        except OSError:
            pass
