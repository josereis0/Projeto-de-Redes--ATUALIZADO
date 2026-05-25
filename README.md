# chat-client

Cliente desktop do sistema de chat — interface gráfica com PyQt6.

## Requisitos

- Python 3.11 ou superior
- PyQt6 e PyQt6-WebEngine

## Instalação

```bash
pip install -r requirements.txt
```

> No Linux pode ser necessário: `pip install PyQt6 PyQt6-WebEngine --break-system-packages`

## Como executar

```bash
# Conecta em 127.0.0.1:5000 (padrão)
python main.py

# Host e porta customizados
python main.py 192.168.1.10 5000
```

O banco local `chat_client.db` (SQLite) é criado automaticamente.

## Arquitetura

| Arquivo / pasta | Responsabilidade |
|---|---|
| `main.py` | Entry point e controlador principal (ChatApp) |
| `database.py` | SQLite local — histórico e contatos |
| `network/connection.py` | Socket TCP + thread de recepção |
| `network/protocol.py` | Definição dos pacotes JSON |
| `ui/login_window.py` | Tela de login e registro |
| `ui/main_window.py` | Lista de contatos com status online/offline |
| `ui/chat_window.py` | Janela de conversa individual |

## Funcionalidades

- **Registro e login** com validação de campos
- **Lista de contatos** com indicadores online (●verde) / offline (●cinza)
- **Mensagens em tempo real** via socket TCP persistente
- **Indicador "digitando..."** com timeout de 2 segundos
- **Notificação de não lidos** (badge numérico na lista)
- **Histórico persistente** em SQLite local
- **Mensagens offline** entregues automaticamente ao reconectar
- **Múltiplas conversas** abertas simultaneamente

## Issues no GitHub (histórico de desenvolvimento)

- `#1` — Estrutura do projeto e banco de dados local
- `#2` — Módulo de conexão TCP com thread de recepção
- `#3` — Tela de login e registro
- `#4` — Tela principal com lista de contatos
- `#5` — Janela de conversa (envio e recebimento)
- `#6` — Indicador "digitando..."
- `#7` — Histórico de conversas (carregamento local)
- `#8` — Recebimento de mensagens offline
