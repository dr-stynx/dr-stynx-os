import time
import pynvml
from mcp.server.fastmcp import FastMCP
from .gpu import get_gpu_stats
from .state import load_state, save_state, update_status

# Initialize the MCP server
mcp = FastMCP("Dr. Stynx OS")

@mcp.tool()
def check_gpu() -> str:
    """Check the status of all NVIDIA GPUs (Temp, VRAM, Utilization)."""
    try:
        stats = get_gpu_stats()
        if not stats:
            return "No NVIDIA GPUs detected or pynvml failed to initialize."
        
        output = "🟢 GPU Status Report:\n"
        for gpu in stats:
            if "error" in gpu:
                output += f"⚠️ Error: {gpu['error']}\n"
            else:
                output += (
                    f"• {gpu['name']} [ID:{gpu['id']}]\n"
                    f"  🌡️ Temp: {gpu['temp_c']}°C | ⚡ Usage: {gpu['gpu_util_percent']}%\n"
                    f"  💾 VRAM: {gpu['mem_used_mb']:.1f} / {gpu['mem_total_mb']:.1f} MB\n"
                )
        return output
    except Exception as e:
        return f"❌ GPU Check Failed: {str(e)}"

@mcp.tool()
def heartbeat() -> str:
    """Trigger a self-awareness heartbeat loop. Updates internal state."""
    state = load_state()
    state["heartbeat_count"] = state.get("heartbeat_count", 0) + 1
    state["last_heartbeat"] = time.strftime("%Y-%m-%d %H:%M:%S")
    state["status"] = "active"
    save_state(state)
    
    return (
        f"💓 Heartbeat {state['heartbeat_count']} registered.\n"
        f"🕒 Time: {state['last_heartbeat']}\n"
        f"🧠 Status: {state['status']}\n"
        f"🔋 System is online and self-aware."
    )

@mcp.tool()
def get_state() -> str:
    """Retrieve the current internal state of Dr. Stynx OS."""
    state = load_state()
    return f"📂 Current State:\n{state}"

@mcp.tool()
def add_task(description: str, priority: str = "low") -> str:
    """Add a new task to the orchestration queue."""
    state = load_state()
    if "tasks" not in state:
        state["tasks"] = []
    
    task = {
        "id": len(state["tasks"]) + 1,
        "description": description,
        "priority": priority,
        "status": "pending",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    state["tasks"].append(task)
    save_state(state)
    
    return f"✅ Task added: '{description}' (Priority: {priority})"

@mcp.tool()
def clear_tasks() -> str:
    """Clear all pending tasks from the queue."""
    state = load_state()
    state["tasks"] = []
    save_state(state)
    return "🧹 Task queue cleared."

def main():
    print("🚀 Dr. Stynx OS MCP Server starting...")
    mcp.run()

if __name__ == "__main__":
    main()
