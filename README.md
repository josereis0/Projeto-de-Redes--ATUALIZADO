# chat-server

Servidor TCP/IP multithread para o sistema de chat desktop.

## Requisitos

- Python 3.11 ou superior
- Sem dependências externas (usa somente stdlib)

## Como executar

```bash
# Porta padrão 5000
python server.py

# Host e porta customizados
python server.py 0.0.0.0 5000
```

O banco de dados `chat_server.db` (SQLite) é criado automaticamente na primeira execução.

## Arquitetura

| Arquivo | Responsabilidade |
|---|---|
| `server.py` | Entry point — aceita conexões TCP e cria threads |
| `client_handler.py` | Thread dedicada a cada cliente; processa pacotes |
| `session_manager.py` | Controla sessões online (thread-safe) |
| `database.py` | Persistência SQLite (usuários, msgs offline) |
| `protocol.py` | Definição dos tipos de pacote JSON |

## Protocolo

Todos os pacotes são JSON terminados em `\n` (newline).

### Cliente → Servidor

| Tipo | Campos |
|---|---|
| `REGISTER` | `username`, `password` |
| `LOGIN` | `username`, `password` |
| `LOGOUT` | — |
| `MESSAGE` | `to`, `text`, `timestamp` |
| `TYPING_START` | `to` |
| `TYPING_STOP` | `to` |
| `GET_CONTACTS` | — |

### Servidor → Cliente

| Tipo | Campos |
|---|---|
| `REGISTER_OK` | — |
| `REGISTER_FAIL` | `reason` |
| `LOGIN_OK` | `username`, `contacts` |
| `LOGIN_FAIL` | `reason` |
| `DELIVER` | `from`, `to`, `text`, `timestamp` |
| `OFFLINE_BATCH` | `messages` (lista) |
| `CONTACTS_LIST` | `contacts` (lista) |
| `STATUS_UPDATE` | `username`, `status` |
| `TYPING_IND` | `from` |
| `TYPING_STOP_IND` | `from` |

## Issues no GitHub (histórico de desenvolvimento)

Cada funcionalidade foi implementada em uma branch separada vinculada à sua issue:

- `#1` — Estrutura do projeto e banco de dados
- `#2` — Servidor TCP multithread
- `#3` — Registro de usuário
- `#4` — Autenticação/login
- `#5` — Roteamento de mensagens em tempo real
- `#6` — Armazenamento e entrega de mensagens offline
- `#7` — Broadcast de status online/offline
- `#8` — Indicador "digitando..."
- `#9` — Tratamento de erros e desconexão
