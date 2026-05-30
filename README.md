# Dr. Stynx OS 🧠

An **MCP (Model Context Protocol)** server providing self-awareness, GPU monitoring, and task orchestration for the Dr. Stynx AI agent.

## Features
- **GPU Monitor**: Real-time NVIDIA GPU stats (VRAM, Temp, Utilization).
- **Heartbeat**: Autonomous self-check loops.
- **State Management**: Persistent memory of current tasks and system status.
- **Task Queue**: Manage background tasks and priorities.

## Usage
```bash
pip install .
dr-stynx-os
```

## Architecture
This server runs on the host machine, exposing tools to any LLM client (LM Studio, Claude, etc.) via stdio transport.
