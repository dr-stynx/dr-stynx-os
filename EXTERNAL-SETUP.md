# 🧠 Dr. Stynx OS - External Access Setup Guide

## Architecture Overview

```
┌─────────────────────────────────────────┐
│         YOUR PHYSICAL HOST             │
│  ┌──────────────────────────────────┐   │
│  │ dr-stynx-os HTTP Server          │   │
│  │ (Port 8080/8081)                 │   │
│  └──────────────────────────────────┘   │
│         ↓ API Calls                     │
│       (JSON-RPC over HTTP)              │
│         ↓                               │
│         ↓                               │
│ ┌─────────────────────────────────────┐ │
│ │  Dr. Stynx Docker VM                │ │ ← YOUR AI ASSISTANT
│ │  (localhost:8111/8000/etc)          │ │   with MCP computer-use
│ │  • GPU Monitoring                   │ │
│  • Heartbeat Loops                    │ │
│  • Task Orchestration                 │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Quick Start (Outside Docker)

### Option 1: Direct Host Access (Recommended for External Use)

Run dr-stynx-os on your host machine:

```bash
# Navigate to installation
cd /path/to/dr-stynx-os

# Start HTTP server binding to all interfaces
python3 src/dr_stynx_os/http_server.py \
  --host 0.0.0.0 \
  --port 8080 \
  --stream-port 8081
```

### Option 2: Using MCP Computer-Use Tool

Since you have computer-use tool access, run:

```bash
# Start the server in background
nohup python3 src/dr_stynx_os/http_server.py --host 0.0.0.0 --port 8080 &

# Or use MCP to execute commands
mcp.computer.execute("python3 /path/to/dr-stynx-os/src/dr_stynx_os/http_server.py --host 0.0.0.0 --port 8080")
```

### Option 3: Standalone Binary Installation

```bash
# Build and install
pip install . --break-system-packages

# Run from any directory
dr-stynx-os-http --host 0.0.0.0 --port 8080 &
```

## API Endpoints (Available to MCP/External Clients)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | POST | JSON-RPC main API |
| `/health` | GET | Health check |
| `/gpu/status` | GET | GPU stats |
| `/state/get` | GET | Internal state |
| `/tasks` | GET/POST | Task management |
| `/heartbeat` | POST | Heartbeat trigger |

## JSON-RPC Examples

```bash
# Get GPU status (for Metatron integration)
curl -X POST "http://YOUR_HOST:8111/" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"gpu.status","params":{},"id":1}'

# Add task to queue
curl -X POST "http://YOUR_HOST:8111/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"task.add",
    "params":{"description":"monitor metatron","priority":"high"},
    "id":null
  }'

# Get heartbeat
curl -X POST "http://YOUR_HOST:8111/" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"heartbeat","params":{},"id":1}'
```

## Environment Variables (Optional)

Add these to your host machine's environment for persistence:

```bash
export DR_STYNX_HOST=0.0.0.0
export DR_STYNX_PORT=8080
export DR_STYNX_STREAM_PORT=8081

# Run with env vars
python3 src/dr_stynx_os/http_server.py \
  --host $DR_STYNX_HOST \
  --port $DR_STYNX_PORT
```

## Security Considerations

⚠️ **Important**: When running outside Docker:

1. **Firewall**: Configure firewall to allow ports 8080, 8081 only from trusted sources
2. **Authentication**: Add API key authentication if exposing to external networks
3. **Network Binding**: Use `--host 127.0.0.1` if you don't need external access

Example with basic auth:

```bash
python3 src/dr_stynx_os/http_server.py \
  --host 0.0.0.0 \
  --port 8080 \
  --auth "your-api-key"
```

## Metatron Integration Pattern

```python
# In your Metatron code, connect to host machine
import requests

def get_gpu_stats(host="YOUR_HOST"):
    url = f"http://{host}:8111/"
    payload = {
        "jsonrpc": "2.0",
        "method": "gpu.status",
        "params": {},
        "id": 1
    }
    
    response = requests.post(url, json=payload)
    return response.json()

# Use the stats for your distributed computing logic
stats = get_gpu_stats()
gpus = stats.get('result', {}).get('gpus', [])
print(f"Detected {len(gpus)} NVIDIA GPUs")
```

## Troubleshooting

### Server Not Starting
```bash
# Check if port is in use
netstat -tlnp | grep 8080

# Kill processes using port 8080
pkill -f "dr-stynx-os"

# Try different port
python3 src/dr_stynx_os/http_server.py --port 8082
```

### API Calls Failing
```bash
# Test direct connectivity
curl http://YOUR_HOST:8111/health

# Check firewall rules
sudo ufw allow 8080/tcp

# Verify server is running
ps aux | grep dr-stynx-os-http
```

## WebSocket Streaming Setup

For real-time GPU updates via WebSocket:

```bash
python3 src/dr_stynx_os/http_server.py \
  --host 0.0.0.0 \
  --port 8080 \
  --stream-port 8081 &

# Connect using WebSocket client
wsconnect -H YOUR_HOST:8111/subscribe.gpu
```

## Summary

**dr-stynx-os runs on your HOST machine (outside Docker)** → Accessible via computer-use MCP tools → Provides GPU monitoring, task orchestration, and heartbeat services for Metatron integration.

Use `drstynx.local` aliases in host's /etc/hosts if desired for cleaner URLs.
