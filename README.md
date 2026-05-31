# Dr. Stynx OS 🧠

An **MCP (Model Context Protocol)** server providing self-awareness, GPU monitoring, persistent memory, and task orchestration for the Dr. Stynx AI agent.

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Dr. Stynx OS Server                │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  GPU     │  │  Tasks   │  │   Memory     │  │
│  │ Monitor  │  │  Queue   │  │  System      │  │
│  │ (Glances)│  │          │  │  (mem0ai)    │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
│                                                 │
│  Transport: SSE (Server-Sent Events)             │
│  Port: 8111                                     │
└─────────────────────────────────────────────────┘
         ▲                    ▲
         │                    │
   MCP Client           Browser Dashboard
   (Metaron, etc.)      (frontend.html)
```

## Quick Start

```bash
# Install
cd /home/assistant/dr-stynx-os
pip install . --break-system-packages

# Start server (MCP over SSE)
python3 -m dr_stynx_os.server

# With watchdog (auto-restart on crash)
bash ./watchdog.sh &
```

**Access**: `http://<host>:8111/` (dashboard + MCP SSE endpoint at `/sse`)

## MCP Tools (11 total)

### System

| Tool | Description |
|------|-------------|
| `check_gpu` | Real-time GPU stats (temp, VRAM, utilization) via Glances API |
| `heartbeat` | Self-awareness check, increments heartbeat counter |
| `get_state` | Get current internal state (tasks, heartbeats, uptime) |

### Tasks

| Tool | Parameters | Description |
|------|-----------|-------------|
| `add_task` | `description`, `priority` (low/medium/high) | Add to task queue |
| `clear_tasks` | — | Clear all tasks |

### Memory (Persistent)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `memory_store` | `text`, `category`, `tags` | Store a memory entry |
| `memory_search` | `query`, `limit`, `category` | Search memories by query |
| `memory_list` | `category`, `limit` | List memories, optionally filtered |
| `memory_delete` | `memory_id` | Delete a specific memory |
| `memory_clear` | — | Clear all memories |
| `memory_stats` | — | Memory usage statistics |

## Dependencies

- **Glances API**: GPU stats come from `https://glances.phaseshift.studio/api/4/gpu`
- **mem0ai**: Persistent memory backend
- **pynvml**: NVIDIA GPU management (fallback)
- **mcp**: Model Context Protocol library

## Running in Production

### Watchdog (Recommended)

The `watchdog.sh` script monitors the server and auto-restarts on failure:

```bash
cd /home/assistant/dr-stynx-os
bash ./watchdog.sh &
```

Features:
- Health checks every 30 seconds
- Auto-restart on crash or unresponsiveness
- Log rotation at 10MB
- Circuit breaker after 5 rapid restarts

### Status Check

```bash
bash ./dr-stynx-os-status.sh
```

Shows: watchdog status, server PID, HTTP health, GPU stats.

### Systemd Service (for systems with systemd)

```bash
# Copy service file
cp ~/.config/systemd/user/dr-stynx-os.service ~/.config/systemd/user/

# Enable and start
systemctl --user daemon-reload
systemctl --user enable --now dr-stynx-os.service
systemctl --user status dr-stynx-os.service
```

## Ports

| Port | Service | Purpose |
|------|---------|---------|
| 8111 | MCP Server (SSE) | Primary endpoint — dashboard + MCP tools |

## External Access

For external hosting (e.g., `dr-stynx.phaseshift.studio`):

1. Run server bound to `0.0.0.0` (default)
2. Set up reverse proxy (nginx/caddy) to forward to `localhost:8111`
3. Ensure DNS points to the host
4. The dashboard auto-detects the host from the request URL

## File Structure

```
dr-stynx-os/
├── src/dr_stynx_os/
│   ├── server.py        # MCP server with SSE transport
│   ├── gpu.py           # GPU monitoring (Glances API)
│   ├── memory.py        # Persistent memory system
│   ├── state.py         # Internal state management
│   └── http_server.py   # Legacy HTTP server (deprecated)
├── frontend.html        # Web dashboard
├── watchdog.sh          # Auto-restart watchdog
├── dr-stynx-os-status.sh  # Status check utility
├── pyproject.toml       # Package config
└── README.md
```

## License

MIT