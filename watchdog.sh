#!/bin/bash
# Dr. Stynx OS Watchdog - runs in background, auto-restarts server
PIDFILE="/home/assistant/dr-stynx-os/logs/dr-stynx-os.pid"
LOGFILE="/home/assistant/dr-stynx-os/logs/watchdog.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOGFILE"; }

start_server() {
    log "Starting server..."
    cd /home/assistant/dr-stynx-os
    PYTHONPATH=/home/assistant/dr-stynx-os/src PYTHONDONTWRITEBYTECODE=1 \
        nohup python3 -m dr_stynx_os.server > /home/assistant/dr-stynx-os/logs/dr-stynx-os.log 2>&1 &
    echo $! > "$PIDFILE"
    disown $!
    log "Server started with PID $(cat $PIDFILE)"
}

while true; do
    # Check if server process exists
    if ! kill -0 $(cat "$PIDFILE" 2>/dev/null) 2>/dev/null; then
        log "Server died, restarting..."
        start_server
        sleep 5
        continue
    fi
    
    # Health check
    if ! curl -s --max-time 3 http://localhost:8111/ > /dev/null 2>&1; then
        log "Server not responding, restarting..."
        kill $(cat "$PIDFILE" 2>/dev/null) 2>/dev/null
        sleep 2
        start_server
    fi
    
    sleep 30
done
