"""
Aplicação de chat desktop — entry point e controlador principal.

Uso:
    python main.py [HOST] [PORT]

Dependências:
    pip install PyQt6
"""
from __future__ import annotations

import sys
import logging
from datetime import datetime, timezone

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QObject, pyqtSignal

import database as DB
from network.connection import Connection
import network.protocol as P
from ui.login_window import LoginWindow
from ui.main_window  import MainWindow
from ui.chat_window  import ChatWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("app")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000


# ── Ponte rede → GUI (thread-safe via Qt signals) ─────────────────────────────

class _Bridge(QObject):
    packet_received = pyqtSignal(dict)
    disconnected    = pyqtSignal()


class ChatApp:
    """Controlador principal da aplicação."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.me   = None    # str | None  — username após login
        self.conn = None    # Connection

        self._open_chats = {}   # dict[str, ChatWindow]

        DB.init_db()

        self.qt_app = QApplication(sys.argv)
        self.qt_app.setStyle("Fusion")

        # Janelas
        self.login_win = LoginWindow()
        self.main_win  = MainWindow()

        # Signals da janela de login
        self.login_win.login_requested.connect(self._do_login)
        self.login_win.register_requested.connect(self._do_register)

        # Signals da janela principal
        self.main_win.contact_selected.connect(self._open_chat)
        self.main_win.logout_requested.connect(self._do_logout)

        # Bridge rede → GUI
        self._bridge = _Bridge()
        self._bridge.packet_received.connect(self._handle_packet)
        self._bridge.disconnected.connect(self._on_disconnected)

        self._connect_to_server()
        self.login_win.show()

    # ── Conexão ───────────────────────────────────────────────────────────────

    def _connect_to_server(self):
        self.conn = Connection(
            on_packet=lambda pkt: self._bridge.packet_received.emit(pkt),
            on_disconnect=lambda: self._bridge.disconnected.emit(),
        )
        try:
            self.conn.connect(self.host, self.port)
        except Exception as e:
            QMessageBox.critical(
                self.login_win,
                "Erro de conexão",
                f"Não foi possível conectar ao servidor {self.host}:{self.port}\n\n{e}",
            )

    # ── Ações do usuário ──────────────────────────────────────────────────────

    def _do_login(self, username: str, password: str):
        if not self.conn.connected:
            self._connect_to_server()
        self.conn.send({
            "type":     P.MSG_LOGIN,
            "username": username,
            "password": password,
        })

    def _do_register(self, username: str, password: str):
        if not self.conn.connected:
            self._connect_to_server()
        self.conn.send({
            "type":     P.MSG_REGISTER,
            "username": username,
            "password": password,
        })

    def _do_logout(self):
        self.conn.send({"type": P.MSG_LOGOUT})
        self.conn.disconnect()
        self.me = None
        # Fecha todas as janelas de chat abertas
        for w in list(self._open_chats.values()):
            w.close()
        self._open_chats.clear()
        self.main_win.hide()
        self.login_win.clear()
        self.login_win.show()
        self._connect_to_server()

    # ── Janelas de chat ───────────────────────────────────────────────────────

    def _open_chat(self, contact: str):
        if contact in self._open_chats:
            w = self._open_chats[contact]
            w.raise_()
            w.activateWindow()
            return

        w = ChatWindow(self.me, contact)
        w.message_sent.connect(self._send_message)
        w.typing_started.connect(
            lambda c: self.conn.send({"type": P.MSG_TYPING_START, "to": c}))
        w.typing_stopped.connect(
            lambda c: self.conn.send({"type": P.MSG_TYPING_STOP, "to": c}))
        w.back_clicked.connect(lambda: self._close_chat(contact))

        # Carrega histórico local (conversas anteriores)
        w.load_history(DB.get_history(self.me, contact))

        # Define status atual do contato
        for c in DB.get_contacts():
            if c["username"] == contact:
                w.set_contact_status(c["status"])
                break

        # Limpa badge de não lidas
        self.main_win.clear_unread(contact)

        self._open_chats[contact] = w
        w.show()

    def _close_chat(self, contact: str):
        if contact in self._open_chats:
            self._open_chats[contact].hide()
            del self._open_chats[contact]

    def _send_message(self, contact: str, text: str):
        ts = datetime.now(timezone.utc).isoformat()
        self.conn.send({
            "type":      P.MSG_SEND,
            "to":        contact,
            "text":      text,
            "timestamp": ts,
        })
        DB.save_message(self.me, contact, self.me, text, ts)
        # Exibe na janela (o servidor NÃO devolve confirmação)
        if contact in self._open_chats:
            self._open_chats[contact].add_message(self.me, text, ts)

    # ── Pacotes recebidos do servidor ─────────────────────────────────────────

    def _handle_packet(self, pkt: dict):
        t = pkt.get("type")

        if t == P.MSG_LOGIN_OK:
            self.me = pkt["username"]
            contacts = pkt.get("contacts", [])
            DB.save_contacts(contacts)
            self.main_win.set_me(self.me)
            self.main_win.load_contacts(contacts)
            self.login_win.hide()
            self.main_win.show()

        elif t == P.MSG_LOGIN_FAIL:
            self.login_win.set_login_error(pkt.get("reason", "Falha no login."))

        elif t == P.MSG_REGISTER_OK:
            self.login_win.set_reg_status("✓ Conta criada! Faça login.", error=False)

        elif t == P.MSG_REGISTER_FAIL:
            self.login_win.set_reg_status(
                pkt.get("reason", "Erro no registro."), error=True)

        elif t == P.MSG_DELIVER:
            self._receive_message(pkt)

        elif t == P.MSG_OFFLINE_BATCH:
            for m in pkt.get("messages", []):
                self._receive_message(m, offline=True)

        elif t == P.MSG_STATUS_UPDATE:
            username = pkt["username"]
            status   = pkt["status"]
            self.main_win.update_status(username, status)
            DB.update_contact_status(username, status)
            if username in self._open_chats:
                self._open_chats[username].set_contact_status(status)

        elif t == P.MSG_TYPING_IND:
            sender = pkt.get("from")
            if sender in self._open_chats:
                self._open_chats[sender].show_typing()

        elif t == P.MSG_TYPING_STOP_IND:
            sender = pkt.get("from")
            if sender in self._open_chats:
                self._open_chats[sender].hide_typing()

        elif t == P.MSG_CONTACTS_LIST:
            contacts = pkt.get("contacts", [])
            DB.save_contacts(contacts)
            self.main_win.load_contacts(contacts)

        else:
            logger.debug("Pacote desconhecido: %s", t)

    def _receive_message(self, pkt: dict, offline: bool = False):
        sender    = pkt.get("from") or pkt.get("sender", "")
        text      = pkt.get("text", "")
        timestamp = pkt.get("timestamp") or datetime.now(timezone.utc).isoformat()
        contact   = sender

        if not sender or not text:
            return

        # Persiste no histórico local
        DB.save_message(self.me, contact, sender, text, timestamp)

        if contact in self._open_chats:
            self._open_chats[contact].add_message(sender, text, timestamp)
            self._open_chats[contact].hide_typing()
        else:
            # Janela não está aberta — incrementa badge
            self.main_win.add_unread(contact)

    def _on_disconnected(self):
        logger.warning("Desconectado do servidor.")
        if self.me:
            QMessageBox.warning(
                self.main_win,
                "Conexão perdida",
                "A conexão com o servidor foi interrompida.\n"
                "Você será redirecionado para o login.",
            )
            self._do_logout()

    # ── Execução ──────────────────────────────────────────────────────────────

    def run(self) -> int:
        return self.qt_app.exec()


def main():
    host = sys.argv[1] if len(sys.argv) >= 2 else DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) >= 3 else DEFAULT_PORT
    app  = ChatApp(host, port)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
