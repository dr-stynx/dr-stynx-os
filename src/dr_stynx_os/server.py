import time
from typing import Optional
from mcp.server.fastmcp import FastMCP

# Optional GPU support
try:
    from .gpu import get_gpu_stats
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    def get_gpu_stats():
        return [{"error": "nvidia-ml-py not available"}]

from .state import load_state, save_state, update_status
from .memory import store_memory, search_memory, list_memories, delete_memory, clear_all_memories, get_memory_stats

# Initialize the MCP server
mcp = FastMCP("Dr. Stynx OS")

# Configure for container access (SSE transport)
mcp.settings.host = "0.0.0.0"
mcp.settings.port = 8111
mcp.settings.transport_security.enable_dns_rebinding_protection = False
mcp.settings.transport_security.allowed_hosts = ["*:*"]
mcp.settings.transport_security.allowed_origins = ["*:*"]

# Serve the HTML dashboard at root
import os
from starlette.responses import HTMLResponse

DASHBOARD_PATH = os.path.join(os.path.expanduser("~"), "dr-stynx-os", "frontend.html")

@mcp.custom_route(path="/", methods=["GET"])
async def serve_dashboard(request):
    """Serve the Dr. Stynx OS dashboard."""
    try:
        with open(DASHBOARD_PATH, "r") as f:
            html = f.read()
        # Inject the actual server URL so the dashboard works from any host
        host = request.url.netloc
        html = html.replace("http://localhost:8111", f"http://{host}")
        return HTMLResponse(content=html)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>🧠 Dr. Stynx OS</h1><p>Dashboard file not found.</p>", status_code=503)

@mcp.tool()
def check_gpu() -> str:
    """Check the status of all NVIDIA GPUs (Temp, VRAM, Utilization)."""
    try:
        stats = get_gpu_stats()
        if not stats:
            return "No NVIDIA GPUs detected or nvidia-ml-py failed to initialize."

        output = "🟢 GPU Status Report:\n"
        for gpu in stats:
            if "error" in gpu:
                output += f"⚠️ Error: {gpu['error']}\n"
            else:
                temp = gpu.get('temp_c', 'N/A')
                util = gpu.get('gpu_util_percent', 'N/A')
                mem_pct = gpu.get('mem_used_percent')
                mem_used = gpu.get('mem_used_mb')
                mem_total = gpu.get('mem_total_mb')

                if mem_total is not None and mem_used is not None:
                    vram = f"{mem_used:.1f} / {mem_total:.1f} MB"
                elif mem_pct is not None:
                    vram = f"{mem_pct:.1f}% used"
                else:
                    vram = "N/A"

                output += (
                    f"• {gpu['name']} [ID:{gpu['id']}]\n"
                    f"  🌡️ Temp: {temp}°C | ⚡ Usage: {util}%\n"
                    f"  💾 VRAM: {vram}\n"
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

@mcp.tool()
def memory_store(text: str, category: str = "general", tags: Optional[str] = None) -> str:
    """
    Store a long-term memory.
    
    Args:
        text: The memory content to store
        category: Category for organization (e.g., "project", "debugging", "decision", "preference")
        tags: Comma-separated tags for filtering (optional)
    """
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    result = store_memory(text, category=category, tags=tag_list)
    return f"✅ Memory stored: {result}"

@mcp.tool()
def memory_search(query: str, limit: int = 5, category: Optional[str] = None) -> str:
    """
    Search memories by semantic similarity.
    
    Args:
        query: Search query
        limit: Max results to return (default 5)
        category: Optional category filter
    """
    results = search_memory(query, limit=limit, category=category)
    if not results:
        return "🔍 No memories found."
    
    output = f"🔍 Found {len(results)} memories:\n"
    for i, r in enumerate(results, 1):
        meta = r.get("metadata", {})
        output += f"  {i}. [{meta.get('category', 'general')}] {r.get('memory', '')}\n"
    return output

@mcp.tool()
def memory_list(category: Optional[str] = None, limit: int = 20) -> str:
    """
    List stored memories, optionally filtered by category.
    
    Args:
        category: Optional category filter
        limit: Max memories to return (default 20)
    """
    results = list_memories(category=category, limit=limit)
    if not results:
        return "📋 No memories stored."
    
    output = f"📋 Stored {len(results)} memories:\n"
    for i, r in enumerate(results, 1):
        meta = r.get("metadata", {})
        output += f"  {i}. [{meta.get('category', 'general')}] {r.get('memory', '')[:100]}\n"
    return output

@mcp.tool()
def memory_delete(memory_id: str) -> str:
    """Delete a memory by ID."""
    success = delete_memory(memory_id)
    if success:
        return f"🗑️ Memory {memory_id} deleted."
    return f"❌ Failed to delete memory {memory_id}."

@mcp.tool()
def memory_clear() -> str:
    """Clear all stored memories."""
    clear_all_memories()
    return "🧹 All memories cleared."

@mcp.tool()
def memory_stats() -> str:
    """Get statistics about stored memories."""
    stats = get_memory_stats()
    output = f"📊 Memory Stats:\n"
    output += f"  Total: {stats['total_memories']}\n"
    output += f"  By category:\n"
    for cat, count in stats.get("by_category", {}).items():
        output += f"    • {cat}: {count}\n"
    output += f"  Storage: {stats['storage_path']}"
    return output

def main():
    print("🚀 Dr. Stynx OS MCP Server starting...")
    mcp.run(transport="sse")

if __name__ == "__main__":
    main()
