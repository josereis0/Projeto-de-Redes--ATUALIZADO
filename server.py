"""
Servidor de chat TCP/IP.

Uso:
    python server.py [HOST] [PORT]

Exemplos:
    python server.py                  # escuta em 0.0.0.0:5000
    python server.py 127.0.0.1 5000
"""
from __future__ import annotations

import socket
import sys
import logging
import signal

import database as DB
from session_manager import SessionManager
from client_handler  import ClientHandler

HOST    = "0.0.0.0"
PORT    = 5000
BACKLOG = 50

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("server")


def main():
    host = sys.argv[1] if len(sys.argv) >= 2 else HOST
    port = int(sys.argv[2]) if len(sys.argv) >= 3 else PORT

    DB.init_db()
    sm = SessionManager()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(BACKLOG)
    logger.info("Servidor escutando em %s:%d", host, port)

    def _shutdown(sig, frame):
        logger.info("Encerrando servidor...")
        server_sock.close()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        try:
            conn, addr = server_sock.accept()
        except OSError:
            break
        handler = ClientHandler(conn, addr, sm)
        handler.start()


if __name__ == "__main__":
    main()
