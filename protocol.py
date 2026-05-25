"""
Protocolo de comunicação do chat.
Todos os pacotes são JSON + newline (\n).
"""

import json

# Tipos de mensagem cliente -> servidor
MSG_REGISTER      = "REGISTER"
MSG_LOGIN         = "LOGIN"
MSG_LOGOUT        = "LOGOUT"
MSG_SEND          = "MESSAGE"
MSG_TYPING_START  = "TYPING_START"
MSG_TYPING_STOP   = "TYPING_STOP"
MSG_GET_CONTACTS  = "GET_CONTACTS"

# Tipos de mensagem servidor -> cliente
MSG_REGISTER_OK   = "REGISTER_OK"
MSG_REGISTER_FAIL = "REGISTER_FAIL"
MSG_LOGIN_OK      = "LOGIN_OK"
MSG_LOGIN_FAIL    = "LOGIN_FAIL"
MSG_DELIVER       = "DELIVER"
MSG_OFFLINE_BATCH = "OFFLINE_BATCH"
MSG_CONTACTS_LIST = "CONTACTS_LIST"
MSG_STATUS_UPDATE = "STATUS_UPDATE"
MSG_TYPING_IND    = "TYPING_IND"
MSG_TYPING_STOP_IND = "TYPING_STOP_IND"
MSG_ERROR         = "ERROR"


def encode(packet: dict) -> bytes:
    """Serializa um pacote para bytes prontos para envio."""
    return (json.dumps(packet, ensure_ascii=False) + "\n").encode("utf-8")


def decode(raw: str) -> dict:
    """Desserializa uma linha JSON recebida."""
    return json.loads(raw.strip())
