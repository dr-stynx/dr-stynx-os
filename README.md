# Dr. Stynx OS 🧠

An **MCP (Model Context Protocol)** server providing self-awareness, GPU monitoring, and task orchestration for the Dr. Stynx AI agent.

## Features

- **GPU Monitor**: Real-time NVIDIA GPU stats (VRAM, Temp, Utilization) via `nvidia-smi` parsing
- **Heartbeat**: Autonomous self-check loops with persistent state tracking
- **State Management**: Persistent memory of current tasks and system status in `~/.dr-stynx-state.json`
- **Task Queue**: Manage background tasks and priorities (add, list, clear)

## Protocols Supported

### 1. MCP Protocol (Default)
```bash
pip install . --break-system-packages
dr-stynx-os        # Stdio transport for LLM clients
```

### 2. JSON-RPC HTTP Server 🌐

**For External Access** (use with port mapping if running in Docker):
```bash
# Start with accessible ports
dr-stynx-os-http --host localhost --port 8111 --stream-port 8222

# OR start on different ports if needed:
dr-stynx-os-http --host 0.0.0.0 --port 8111 --stream-port 8222
```

**Access via HTTP**: `http://localhost:8111/`  
**WebSocket Streaming**: `ws://localhost:8222/`  
**HTML Dashboard**: `http://localhost:8000/frontend.html`

## JSON-RPC Methods (HTTP)

All endpoints use **JSON-RPC 2.0** protocol. Example request:

```json
{
  "jsonrpc": "2.0",
  "method": "gpu.status",
  "params": {},
  "id": null
}
```

### Available Methods

| Method | Description | Response |
|--------|-------------|----------|
| `health` | Check server status | `{"status": "ok", "heartbeat_count": N}` |
| `gpu.status` | Get GPU stats | `{"gpus": [{"id", "name", "temp_c", "mem_total_mb", "mem_used_mb", "gpu_util_percent"}]}` |
| `state.get` | Get internal state | `{...state object}` |
| `task.add`<br/>`tasks.add` | Add a task | `{"id": N, "status": "success"}` |
| `task.clear`<br/>`tasks.clear` | Clear all tasks | `{"status": "success"}` |
| `heartbeat` | Trigger self-awareness | `{"heartbeat_count": N, "last_heartbeat": "..."}` |
| `task.list`<br/>`tasks.list` | List all tasks | `{...tasks array}` |

## WebSocket Streaming (WebSockets)

Connect to `ws://localhost:8222/` for real-time GPU updates and state changes. The server will broadcast:

- `gpu.update` - GPU status changes
- `heartbeat.ping` - Regular pings
- `state.changed` - State modifications

## Usage Examples

### Using MCP Protocol (stdio)

```bash
dr-stynx-os
# Available via any LLM client supporting MCP stdio transport
```

### Using JSON-RPC HTTP

```bash
# Start the server on localhost:8111
dr-stynx-os-http --host localhost --port 8080 &

# Check GPU status
curl -X POST http://localhost:8111 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"gpu.status","params":{}}'

# Add a task
curl -X POST http://localhost:8111 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"task.add","params":{"description":"monitor metatron","priority":"high"},"id":null}'
```

### Using HTML Dashboard (Web Interface)

Start the dashboard server:
```bash
python3 -m http.server 8000 --bind 0.0.0.0 &
# OR use built-in dashboard runner:
dr-stynx-os-http-dashboard &
```

**Access via browser**: `http://localhost:8000/frontend.html`

### Using WebSocket

```bash
# Subscribe to GPU updates (requires WebSocket client)
curl -ws ws://localhost:8222/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"subscribe.gpu","params":{},"id":1}'
```

## Architecture

This server has two modes:

| Mode | Protocol | Transport | Best For |
|------|----------|-----------|----------|
| MCP Server | JSON-RPC 2.0 | Stdio/WS | LLM clients (Claude, etc.) |
| HTTP Server | JSON-RPC 2.0 | HTTP | Metatron integration |

**Metatron Integration**: Use the `dr-stynx-os-http` binary to expose GPU monitoring and task orchestration as REST endpoints that can be called from any language via JSON-RPC protocol.

## Quick Start

```bash
# Install
pip install . --break-system-packages

# Run MCP server (for LLM clients)
dr-stynx-os

# OR run HTTP/JSON-RPC server + HTML Dashboard:
dr-stynx-os-http --host localhost --port 8080 &
python3 -m http.server 8000 --bind 0.0.0.0 &

# Check GPU status via MCP tool
check_gpu  # via MCP tool

# Or via HTTP JSON-RPC
curl -X POST http://localhost:8111 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"health","params":{},"id":1}'
```

## Ports Summary

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| HTML Dashboard | 8000 | HTTP/HTML | Web interface (frontend.html) |
| JSON-RPC API | 8080 | HTTP + POST | REST API for Metatron |
| WebSocket Stream | 8081 | WebSocket | Real-time GPU updates |

## License

MIT