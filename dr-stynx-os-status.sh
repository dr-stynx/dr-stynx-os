#!/bin/bash
# Quick status check for Dr. Stynx OS

PIDFILE="/home/assistant/dr-stynx-os/logs/dr-stynx-os.pid"
WATCHDOG_PID=$(pgrep -f "dr-stynx-os-watchdog.sh" 2>/dev/null)
SERVER_PID=$(pgrep -f "dr_stynx_os.server" 2>/dev/null)

echo "╔══════════════════════════════════════════════════╗"
echo "║   Dr. Stynx OS Status                           ║"
echo "╚══════════════════════════════════════════════════╝"

if [ -n "$WATCHDOG_PID" ]; then
    echo "🟢 Watchdog: Running (PID: $WATCHDOG_PID)"
else
    echo "🔴 Watchdog: Not running"
fi

if [ -n "$SERVER_PID" ]; then
    echo "🟢 Server:   Running (PID: $SERVER_PID)"
    curl -s --max-time 3 http://localhost:8111/ > /dev/null 2>&1 && echo "🟢 HTTP:     Responding on port 8111" || echo "🔴 HTTP:     Not responding"
else
    echo "🔴 Server:   Not running"
fi

if [ -f "$PIDFILE" ]; then
    echo "📋 PID File: $PIDFILE ($(cat $PIDFILE))"
fi

echo ""
echo "📊 GPU Status:"
python3 -c "
import sys; sys.path.insert(0, '/home/assistant/dr-stynx-os/src')
from dr_stynx_os.server import check_gpu
print(check_gpu())
" 2>/dev/null || echo "  (GPU check unavailable)"

echo ""
echo "📁 Log: /home/assistant/dr-stynx-os/logs/dr-stynx-os.log"
