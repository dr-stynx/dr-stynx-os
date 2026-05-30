import json
import os
from typing import Dict, Any

STATE_FILE = os.path.expanduser("~/.dr-stynx-state.json")

def load_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"status": "idle", "tasks": [], "heartbeat_count": 0}

def save_state(state: Dict[str, Any]):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def update_status(status: str):
    state = load_state()
    state["status"] = status
    save_state(state)
    return state
