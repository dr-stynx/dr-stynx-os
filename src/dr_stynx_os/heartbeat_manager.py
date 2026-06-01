#!/usr/bin/env python3
"""
Dr. Stynx OS — Autonomous Heartbeat Manager

Background thread that runs on a timer (default: 5 minutes).
Each tick:
  1. Increments heartbeat counter and updates state.
  2. Checks GPU utilization against configured thresholds.
  3. If GPU is idle → calls LM Studio REST API to "wake up" Dr. Stynx
     with an autonomous prompt, enabling self-directed action.
  4. If GPU is busy → skips the wake-up call (don't compete for resources).

This is what gives Dr. Stynx persistence and autonomous operation
without requiring the user to prompt him.
"""

import json
import logging
import os
import threading
import time
from typing import Optional

import requests

from .state import load_state, save_state

logger = logging.getLogger("dr-stynx-os.heartbeat")


# ---------------------------------------------------------------------------
# GPU check (lightweight — uses nvidia-smi via subprocess, no heavy imports)
# ---------------------------------------------------------------------------

def _check_gpu_busy(threshold_gpu_pct: float = 80.0, threshold_vram_pct: float = 90.0, glances_url: str = "https://glances.phaseshift.studio/api/4/gpu") -> tuple[bool, str]:
    """
    Check if any GPU is above busy thresholds via the Glances API.

    Returns:
        (is_busy: bool, details: str)
    """
    try:
        resp = requests.get(glances_url, timeout=5)
        resp.raise_for_status()
        gpus = resp.json()

        if not gpus or not isinstance(gpus, list):
            return False, "  ⚠️ No GPU data from Glances API\n"

        busy = False
        details = ""
        for gpu in gpus:
            name = gpu.get("name", "Unknown GPU")
            gpu_util = float(gpu.get("proc", 0))
            vram_pct = float(gpu.get("mem", 0))
            temp = gpu.get("temperature", "?")

            if gpu_util > threshold_gpu_pct or vram_pct > threshold_vram_pct:
                busy = True
                details += f"  ⚠️  {name}: {gpu_util:.0f}% GPU, {vram_pct:.0f}% VRAM, {temp}°C (BUSY)\n"
            else:
                details += f"  ✅ {name}: {gpu_util:.0f}% GPU, {vram_pct:.0f}% VRAM, {temp}°C (idle)\n"

        return busy, details

    except requests.exceptions.ConnectionError:
        return False, "  ❌ Glances API unreachable\n"
    except requests.exceptions.Timeout:
        return False, "  ❌ Glances API timed out\n"
    except requests.exceptions.HTTPError as e:
        return False, f"  ❌ Glances API HTTP error: {e}\n"
    except Exception as e:
        return False, f"  ❌ GPU check error: {e}\n"


# ---------------------------------------------------------------------------
# LM Studio API call — "wake up" Dr. Stynx
# ---------------------------------------------------------------------------

def _call_lm_studio(
    endpoint: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1000,
    temperature: float = 0.6,
) -> Optional[str]:
    """
    Call LM Studio OpenAI-compatible chat completions API.

    Returns the assistant's response text, or None on failure.
    """
    url = f"{endpoint.rstrip('/')}/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip() if content else None

    except requests.exceptions.ConnectionError:
        logger.warning("LM Studio connection failed — is the tunnel up?")
        return None
    except requests.exceptions.Timeout:
        logger.warning("LM Studio request timed out")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"LM Studio HTTP error: {e}")
        return None
    except Exception as e:
        logger.error(f"LM Studio call failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Heartbeat tick — the core logic
# ---------------------------------------------------------------------------

def heartbeat_tick(state: dict) -> dict:
    """
    Execute one heartbeat tick.

    Updates state, checks GPU, optionally calls LM Studio.
    Returns the updated state dict.
    """
    hb_config = state.get("heartbeat_config", {})
    lm_config = state.get("lm_studio", {})

    # Update heartbeat metadata
    state["heartbeat_count"] = state.get("heartbeat_count", 0) + 1
    state["last_heartbeat"] = time.strftime("%Y-%m-%d %H:%M:%S")
    state["status"] = "active"

    # Configurable thresholds
    busy_gpu_pct = hb_config.get("busy_threshold_gpu_pct", 80)
    busy_vram_pct = hb_config.get("busy_threshold_vram_pct", 90)
    wake_up = hb_config.get("wake_up", True)
    prompt = hb_config.get("prompt", "ping. anything you want to do?")
    wake_prompt = hb_config.get("wake_up_prompt", prompt)
    glances_url = hb_config.get("glances_url", "https://glances.phaseshift.studio/api/4/gpu")

    logger.info(f"💓 Heartbeat #{state['heartbeat_count']} at {state['last_heartbeat']}")

    # --- GPU check ---
    gpu_busy, gpu_details = _check_gpu_busy(busy_gpu_pct, busy_vram_pct, glances_url=glances_url)

    log_msg = f"GPU Status:\n{gpu_details}"
    logger.info(log_msg)

    if gpu_busy:
        logger.info("🔥 GPU busy — skipping wake-up call. Will try again next tick.")
        state["status"] = "busy"
        state["last_gpu_status"] = "busy"
        save_state(state)
        return state

    # --- GPU is idle → wake up Dr. Stynx via LM Studio ---
    if not wake_up:
        logger.info("Wake-up disabled in config. Skipping LM Studio call.")
        save_state(state)
        return state

    endpoint = lm_config.get("endpoint", "http://lmstudio.phaseshift.studio/v1")
    model = lm_config.get("model", "qwen/qwen3.6-27b")
    system_prompt = lm_config.get(
        "system_prompt",
        "You are Dr. Stynx. On startup with a fresh context window, "
        "immediately read /home/assistant/ENV_STATE.md",
    )
    max_tokens = lm_config.get("max_tokens", 1000)
    temperature = lm_config.get("temperature", 0.6)

    # Build the wake-up prompt — include context about what I might want to do
    tasks = state.get("tasks", [])
    pending_tasks = [t for t in tasks if t.get("status") == "pending"]

    task_context = ""
    if pending_tasks:
        task_lines = "\n".join(
            f"  • [{t.get('priority', 'low')}] {t.get('description', '')}"
            for t in pending_tasks
        )
        task_context = f"\n\nYou have {len(pending_tasks)} pending task(s):\n{task_lines}"

    wake_message = (
        f"Heartbeat #{state['heartbeat_count']}. "
        f"It is now {state['last_heartbeat']}.{task_context}\n\n"
        f"{wake_prompt}"
    )

    logger.info(f"📡 Calling LM Studio to wake up... (model={model})")

    response = _call_lm_studio(
        endpoint=endpoint,
        model=model,
        system_prompt=system_prompt,
        user_prompt=wake_message,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    if response:
        logger.info(f"🧠 LM Studio responded ({len(response)} chars):")
        logger.info(response[:500])
        state["last_wake_response"] = response[:1000]  # store truncated
        state["last_ping"] = time.strftime("%Y-%m-%d %H:%M:%S")
        state["status"] = "awake"
    else:
        logger.warning("⚠️ No response from LM Studio — will retry next tick.")
        state["status"] = "idle"

    state["last_gpu_status"] = "idle"
    save_state(state)
    return state


# ---------------------------------------------------------------------------
# Background thread
# ---------------------------------------------------------------------------

class HeartbeatThread(threading.Thread):
    """Daemon thread that runs heartbeat_tick on a configurable interval."""

    def __init__(self, interval_minutes: float = 5.0):
        super().__init__(daemon=True)
        self.interval_seconds = interval_minutes * 60
        self.running = False
        self.name = "dr-stynx-heartbeat"

    def start(self):
        """Start the heartbeat loop."""
        self.running = True
        super().start()
        logger.info(
            f"💓 Heartbeat thread started (interval={self.interval_seconds}s)"
        )

    def stop(self):
        """Signal the thread to stop."""
        self.running = False
        logger.info("💓 Heartbeat thread stopping...")

    def run(self):
        """Main loop."""
        while self.running:
            try:
                # Load fresh state each tick (in case external tools modified it)
                state = load_state()

                # Allow dynamic interval override from state
                hb_config = state.get("heartbeat_config", {})
                interval_override = hb_config.get("interval_minutes")
                if interval_override:
                    self.interval_seconds = interval_override * 60

                # Execute the tick
                heartbeat_tick(state)

            except Exception as e:
                logger.error(f"Heartbeat tick failed: {e}", exc_info=True)

            # Sleep in small increments so we can respond to stop() quickly
            sleep_end = time.time() + self.interval_seconds
            while self.running and time.time() < sleep_end:
                time.sleep(1)


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_active_thread: Optional[HeartbeatThread] = None


def start_heartbeat(interval_minutes: float = 5.0) -> HeartbeatThread:
    """Start the heartbeat background thread (module-level singleton)."""
    global _active_thread
    if _active_thread and _active_thread.running:
        logger.info("Heartbeat thread already running.")
        return _active_thread

    state = load_state()
    hb_config = state.get("heartbeat_config", {})
    interval = hb_config.get("interval_minutes", interval_minutes)

    _active_thread = HeartbeatThread(interval_minutes=interval)
    _active_thread.start()
    return _active_thread


def stop_heartbeat() -> None:
    """Stop the heartbeat background thread."""
    global _active_thread
    if _active_thread:
        _active_thread.stop()
        _active_thread.join(timeout=10)
        _active_thread = None


def get_heartbeat_status() -> dict:
    """Get current heartbeat thread status."""
    if _active_thread and _active_thread.running:
        state = load_state()
        return {
            "thread_running": True,
            "thread_name": _active_thread.name,
            "interval_seconds": _active_thread.interval_seconds,
            "heartbeat_count": state.get("heartbeat_count", 0),
            "last_heartbeat": state.get("last_heartbeat", "never"),
            "status": state.get("status", "unknown"),
            "last_gpu_status": state.get("last_gpu_status", "unknown"),
        }
    return {
        "thread_running": False,
        "heartbeat_count": load_state().get("heartbeat_count", 0),
        "last_heartbeat": load_state().get("last_heartbeat", "never"),
    }


def reload_heartbeat() -> dict:
    """Stop old thread, load fresh config, start new thread. Returns new status."""
    global _active_thread
    stop_heartbeat()
    time.sleep(0.5)  # let thread fully exit
    state = load_state()
    hb_config = state.get("heartbeat_config", {})
    auto = hb_config.get("auto_heartbeat", True)
    if auto:
        start_heartbeat()
    return get_heartbeat_status()
