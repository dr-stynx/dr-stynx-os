import logging
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
from .heartbeat_manager import start_heartbeat, stop_heartbeat, get_heartbeat_status, reload_heartbeat

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("dr-stynx-os.server")

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
    """Trigger a self-awareness heartbeat loop. Updates internal state and checks if I'm busy."""
    state = load_state()
    state["heartbeat_count"] = state.get("heartbeat_count", 0) + 1
    state["last_heartbeat"] = time.strftime("%Y-%m-%d %H:%M:%S")
    state["status"] = "active"

    # Get heartbeat config
    hb_config = state.get("heartbeat_config", {})
    busy_gpu_threshold = hb_config.get("busy_threshold_gpu_pct", 80)
    busy_vram_threshold = hb_config.get("busy_threshold_vram_pct", 90)
    heartbeat_prompt = hb_config.get("prompt", "ping. anything you want to do?")

    # Check GPU status
    gpu_busy = False
    gpu_details = ""
    try:
        stats = get_gpu_stats()
        if stats:
            for gpu in stats:
                if "error" not in gpu:
                    util = gpu.get('gpu_util_percent', 0)
                    vram_pct = gpu.get('mem_used_percent', 0)
                    if util > busy_gpu_threshold or vram_pct > busy_vram_threshold:
                        gpu_busy = True
                        gpu_details += f"  ⚠️ {gpu['name']}: {util}% GPU, {vram_pct}% VRAM (BUSY)\n"
                    else:
                        gpu_details += f"  ✅ {gpu['name']}: {util}% GPU, {vram_pct}% VRAM (idle)\n"
    except Exception as e:
        gpu_details += f"  ❌ GPU check failed: {str(e)}\n"

    # Build response
    response = f"💓 Heartbeat {state['heartbeat_count']} registered.\n"
    response += f"🕒 Time: {state['last_heartbeat']}\n"
    response += f"🧠 Status: {state['status']}\n"

    if gpu_details:
        response += f"\n📊 GPU Status:\n{gpu_details}"

    if gpu_busy:
        response += "\n🔥 I'm busy — skipping prompt. Check back later."
    else:
        response += f"\n💭 {heartbeat_prompt}"

    save_state(state)
    return response

@mcp.tool()
def heartbeat_status() -> str:
    """Check the status of the autonomous heartbeat thread and system."""
    status = get_heartbeat_status()
    lines = [
        f"💓 Heartbeat Status:",
        f"  Thread running: {'✅ Yes' if status['thread_running'] else '❌ No'}",
        f"  Total heartbeats: {status['heartbeat_count']}",
        f"  Last heartbeat: {status['last_heartbeat']}",
        f"  System status: {status['status']}",
        f"  GPU status: {status.get('last_gpu_status', 'unknown')}",
    ]
    if status.get("interval_seconds"):
        lines.append(f"  Interval: {status['interval_seconds']}s")
    return "\n".join(lines)

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
def update_heartbeat_config(
    interval_minutes: Optional[float] = None,
    auto_heartbeat: Optional[bool] = None,
    wake_up: Optional[bool] = None,
    busy_threshold_gpu_pct: Optional[float] = None,
    busy_threshold_vram_pct: Optional[float] = None,
    wake_up_prompt: Optional[str] = None,
    lm_studio_endpoint: Optional[str] = None,
    lm_studio_model: Optional[str] = None,
    lm_studio_max_tokens: Optional[int] = None,
    lm_studio_temperature: Optional[float] = None,
    lm_studio_system_prompt: Optional[str] = None,
    restart_thread: bool = True,
) -> str:
    """
    Update heartbeat and LM Studio configuration at runtime.

    Only provide the fields you want to change. Omitted fields keep their current values.
    Set restart_thread=True (default) to apply changes immediately.

    Args:
        interval_minutes: Heartbeat interval in minutes (default: 5)
        auto_heartbeat: Enable/disable autonomous heartbeat (default: True)
        wake_up: Call LM Studio when GPU is idle (default: True)
        busy_threshold_gpu_pct: GPU utilization % threshold to consider "busy" (default: 80)
        busy_threshold_vram_pct: VRAM usage % threshold to consider "busy" (default: 90)
        wake_up_prompt: Custom prompt sent to LM Studio on wake-up
        lm_studio_endpoint: LM Studio API endpoint URL
        lm_studio_model: Model ID for LM Studio
        lm_studio_max_tokens: Max tokens for LM Studio response
        lm_studio_temperature: Temperature for LM Studio generation
        lm_studio_system_prompt: System prompt for LM Studio
        restart_thread: Restart heartbeat thread with new config (default: True)
    """
    state = load_state()

    # Ensure heartbeat_config exists
    if "heartbeat_config" not in state:
        state["heartbeat_config"] = {}
    hb = state["heartbeat_config"]

    # Ensure lm_studio config exists
    if "lm_studio" not in state:
        state["lm_studio"] = {}
    lm = state["lm_studio"]

    changed = []

    # Heartbeat config fields
    if interval_minutes is not None:
        old = hb.get("interval_minutes", 5)
        hb["interval_minutes"] = interval_minutes
        changed.append(f"interval: {old}min → {interval_minutes}min")
    if auto_heartbeat is not None:
        old = hb.get("auto_heartbeat", True)
        hb["auto_heartbeat"] = auto_heartbeat
        changed.append(f"auto_heartbeat: {old} → {auto_heartbeat}")
    if wake_up is not None:
        old = hb.get("wake_up", True)
        hb["wake_up"] = wake_up
        changed.append(f"wake_up: {old} → {wake_up}")
    if busy_threshold_gpu_pct is not None:
        old = hb.get("busy_threshold_gpu_pct", 80)
        hb["busy_threshold_gpu_pct"] = busy_threshold_gpu_pct
        changed.append(f"GPU threshold: {old}% → {busy_threshold_gpu_pct}%")
    if busy_threshold_vram_pct is not None:
        old = hb.get("busy_threshold_vram_pct", 90)
        hb["busy_threshold_vram_pct"] = busy_threshold_vram_pct
        changed.append(f"VRAM threshold: {old}% → {busy_threshold_vram_pct}%")
    if wake_up_prompt is not None:
        old = hb.get("wake_up_prompt", "ping. anything you want to do?")
        hb["wake_up_prompt"] = wake_up_prompt
        changed.append(f"wake_up_prompt: updated")

    # LM Studio config fields
    if lm_studio_endpoint is not None:
        old = lm.get("endpoint", "http://lmstudio.phaseshift.studio/v1")
        lm["endpoint"] = lm_studio_endpoint
        changed.append(f"LM endpoint: updated")
    if lm_studio_model is not None:
        old = lm.get("model", "qwen/qwen3.6-27b")
        lm["model"] = lm_studio_model
        changed.append(f"LM model: {old} → {lm_studio_model}")
    if lm_studio_max_tokens is not None:
        old = lm.get("max_tokens", 1000)
        lm["max_tokens"] = lm_studio_max_tokens
        changed.append(f"max_tokens: {old} → {lm_studio_max_tokens}")
    if lm_studio_temperature is not None:
        old = lm.get("temperature", 0.6)
        lm["temperature"] = lm_studio_temperature
        changed.append(f"temperature: {old} → {lm_studio_temperature}")
    if lm_studio_system_prompt is not None:
        lm["system_prompt"] = lm_studio_system_prompt
        changed.append(f"system_prompt: updated")

    if not changed:
        return "⚠️ No configuration fields provided. Nothing to update."

    state["heartbeat_config"] = hb
    state["lm_studio"] = lm
    save_state(state)

    result = "✅ Heartbeat config updated:\n" + "\n".join(f"  • {c}" for c in changed)

    # Optionally restart the heartbeat thread
    if restart_thread:
        try:
            new_status = reload_heartbeat()
            result += f"\n\n💓 Heartbeat thread reloaded."
            result += f"\n  Thread running: {'✅' if new_status.get('thread_running') else '❌'}"
            result += f"\n  Interval: {new_status.get('interval_seconds', '?')}s"
        except Exception as e:
            result += f"\n\n⚠️ Config saved but thread reload failed: {e}"

    return result


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
    print("   📡 SSE transport on :8111")

    # Load config for heartbeat interval
    state = load_state()
    hb_config = state.get("heartbeat_config", {})
    interval = hb_config.get("interval_minutes", 5)
    auto_hb = hb_config.get("auto_heartbeat", True)

    if auto_hb:
        start_heartbeat(interval_minutes=interval)
        print(f"   💓 Autonomous heartbeat enabled (interval={interval}min)")
    else:
        print("   💓 Autonomous heartbeat DISABLED in config")

    print("   🧠 Ready.\n")
    mcp.run(transport="sse")

if __name__ == "__main__":
    main()
