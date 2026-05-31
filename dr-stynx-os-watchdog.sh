#!/bin/bash
# Dr. Stynx OS Watchdog - Auto-restart server on crash
LOGDIR="/home/assistant/dr-stynx-os/logs"
LOGFILE="$LOGDIR/dr-stynx-os.log"
PIDFILE="$LOGDIR/dr-stynx-os.pid"
MAX_LOG_SIZE=10485760
RESTART_COUNT=0
MAX_RESTARTS=5
RESTART_WINDOW=60

mkdir -p "$LOGDIR"

rotate_log() {
    if [ -f "$LOGFILE" ] && [ $(stat -c%s "$LOGFILE" 2>/dev/null || echo 0) -gt $MAX_LOG_SIZE ]; then
        mv "$LOGFILE" "$LOGFILE.old"
        echo "[Watchdog] Log rotated at $(date)" > "$LOGFILE"
    fi
}

cleanup() {
    echo "[Watchdog] Stopping Dr. Stynx OS"
    kill $(cat $PIDFILE 2>/dev/null) 2>/dev/null
    rm -f "$PIDFILE"
    exit 0
}

trap cleanup SIGINT SIGTERM

start_server() {
    echo "[Watchdog] Starting Dr. Stynx OS server at $(date)"
    
    PYTHONPATH=/home/assistant/dr-stynx-os/src \
    PYTHONDONTWRITEBYTECODE=1 \
    nohup python3 -m dr_stynx_os.server >> "$LOGFILE" 2>&1 &
    
    SERVER_PID=$!
    echo $SERVER_PID > "$PIDFILE"
    echo "[Watchdog] Server PID: $SERVER_PID"
    
    for i in {1..15}; do
        if curl -s http://localhost:8111/ > /dev/null 2>&1; then
            echo "[Watchdog] ✅ Server is up and responding"
            return 0
        fi
        sleep 1
    done
    
    echo "[Watchdog] ❌ Server failed to start within 15 seconds"
    return 1
}

echo "╔══════════════════════════════════════════════════╗"
echo "║   Dr. Stynx OS Watchdog v1.0                    ║"
echo "║   Monitoring: localhost:8111                     ║"
echo "║   Log: $LOGFILE"
echo "╚══════════════════════════════════════════════════╝"

start_server
if [ $? -ne 0 ]; then
    echo "[Watchdog] Fatal: Could not start server. Exiting."
    exit 1
fi

while true; do
    sleep 10
    
    if ! kill -0 $(cat $PIDFILE 2>/dev/null) 2>/dev/null; then
        RESTART_COUNT=$((RESTART_COUNT + 1))
        echo "[Watchdog] ⚠️ Server crashed (restart #$RESTART_COUNT)"
        
        if [ $RESTART_COUNT -gt $MAX_RESTARTS ]; then
            echo "[Watchdog] 🚨 Too many restarts. Circuit breaker engaged."
            sleep $RESTART_WINDOW
            RESTART_COUNT=0
        fi
        
        rotate_log
        start_server
    else
        if ! curl -s --max-time 3 http://localhost:8111/ > /dev/null 2>&1; then
            echo "[Watchdog] ⚠️ Server not responding, restarting..."
            RESTART_COUNT=$((RESTART_COUNT + 1))
            kill $(cat $PIDFILE 2>/dev/null) 2>/dev/null
            sleep 2
            rotate_log
            start_server
        fi
    fi
done
