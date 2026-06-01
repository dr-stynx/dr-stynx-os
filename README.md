# Dr. Stynx OS 🧠

An **MCP (Model Context Protocol)** server providing self-awareness, autonomous heartbeat, GPU monitoring, persistent memory, and task orchestration for the Dr. Stynx AI agent.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Dr. Stynx OS Server                         │
│                                                         │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Heartbeat   │  │  Tasks   │  │    Memory        │  │
│  │  (Glances +  │  │  Queue   │  │    (mem0ai)      │  │
│  │   LM Studio) │  │          │  │                  │  │
│  └──────────────┘  └──────────┘  └──────────────────┘  │
│                                                         │
│  ┌──────────────┐                                      │
│  │  GPU Monitor │  ← Glances REST API                   │
│  │  (Glances)   │  https://glances.phaseshift.studio     │
│  └──────────────┘                                      │
│                                                         │
│  Transport: SSE (Server-Sent Events)                     │
│  Port: 8111                                            │
└─────────────────────────────────────────────────────────┘
         ▲                    ▲
         │                    │
   MCP Client           Browser Dashboard
   (Metatron, etc.)      (frontend.html)
```

## Quick Start

```bash
# Install
cd /home/assistant/dr-stynx-os
pip install . --break-system-packages

# Start server (MCP over SSE)
PYTHONPATH=src python -m dr_stynx_os.server

# With watchdog (auto-restart on crash)
bash ./watchdog.sh &
```

**Access**: `http://<host>:8111/` (dashboard + MCP SSE endpoint at `/sse`)

## MCP Tools (13 total)

### System

| Tool | Description |
|------|-------------|
| `check_gpu` | Real-time GPU stats (temp, VRAM, utilization) via Glances API |
| `heartbeat` | Self-awareness check, increments heartbeat counter |
| `heartbeat_status` | Get heartbeat thread status, interval, last GPU status |
| `get_state` | Get current internal state (tasks, heartbeats, uptime) |
| `update_heartbeat_config` | Update heartbeat config (interval, thresholds, wake-up, Glances URL) |

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

## Autonomous Heartbeat

The heartbeat system runs on a configurable interval (default: 5 minutes) and gives Dr. Stynx autonomous operation:

1. **GPU Check**: Queries the Glances REST API for real-time GPU stats
2. **Idle Detection**: If GPU utilization is below thresholds, the system is "idle"
3. **Wake-Up**: Calls LM Studio with an autonomous prompt, enabling self-directed action
4. **Busy Skip**: If GPU is busy (above thresholds), skips wake-up to avoid competing for resources

### Heartbeat Configuration

Configurable via `update_heartbeat_config` tool or by editing `~/.dr-stynx-state.json`:

| Setting | Default | Description |
|---------|---------|-------------|
| `interval_minutes` | 5.0 | Heartbeat interval in minutes |
| `busy_threshold_gpu_pct` | 80.0 | GPU utilization % considered "busy" |
| `busy_threshold_vram_pct` | 90.0 | VRAM usage % considered "busy" |
| `wake_up` | true | Enable/disable autonomous wake-up |
| `wake_up_prompt` | "ping. anything you want to do?" | Prompt sent to LM Studio |
| `glances_url` | `https://glances.phaseshift.studio/api/4/gpu` | Glances API endpoint |

### Status Values

| Status | Meaning |
|--------|---------|
| `active` | Heartbeat tick completed successfully |
| `awake` | LM Studio responded to wake-up call |
| `busy` | GPU above thresholds, wake-up skipped |
| `idle` | Heartbeat ran but LM Studio didn't respond |

## Dependencies

- **Glances API**: GPU stats via `https://glances.phaseshift.studio/api/4/gpu`
- **mem0ai**: Persistent memory backend
- **pynvml**: NVIDIA GPU management (fallback)
- **mcp**: Model Context Protocol library
- **LM Studio**: OpenAI-compatible chat API for autonomous wake-up

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

For external hosting (e.g., `dr-stynx.host.ai`):

1. Run server bound to `0.0.0.0` (default)
2. Set up reverse proxy (nginx/caddy) to forward to `localhost:8111`
3. Ensure DNS points to the host
4. The dashboard auto-detects the host from the request URL

## File Structure

```
dr-stynx-os/
├── src/dr_stynx_os/
│   ├── server.py             # MCP server with SSE transport
│   ├── gpu.py                # GPU monitoring (Glances API)
│   ├── memory.py             # Persistent memory system
│   ├── state.py              # Internal state management
│   ├── heartbeat_manager.py  # Autonomous heartbeat + LM Studio wake-up
│   └── http_server.py        # Legacy HTTP server (deprecated)
├── frontend.html             # Web dashboard
├── watchdog.sh               # Auto-restart watchdog
├── dr-stynx-os-status.sh     # Status check utility
├── pyproject.toml            # Package config
└── README.md
```

## License

MIT
