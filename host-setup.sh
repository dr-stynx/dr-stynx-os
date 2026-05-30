#!/bin/bash
# =============================================================================
# Dr. Stynx OS - Host Machine Setup Script
# 
# This script prepares dr-stynx-os to run on your physical host machine
# for external access via computer-use MCP tool or direct API calls.
# =============================================================================

set -e

echo "🧠 Dr. Stynx OS - External Host Setup"
echo "======================================"
echo ""

# Function to display current state
show_status() {
    echo ""
    echo "=== Current Dr. Stynx Server Status ==="
    if pgrep -f "dr-stynx-os-http"; then
        echo "✅ Server is running"
        ps aux | grep dr-stynx-os-http | grep -v grep | head -1
    else
        echo "❌ Server not running"
    fi
    
    # Check ports
    echo ""
    echo "=== Listening Ports ==="
    netstat -tlnp 2>/dev/null | grep -E ":808[0-9]" | head -3 || \
    lsof -i :8080 -i :8081 2>/dev/null | head -5 || \
    echo "(Use netstat or lsof to check ports)"
    
    # Check if installed
    if command -v dr-stynx-os-http &>/dev/null; then
        echo ""
        echo "=== Available Commands ==="
        echo "  dr-stynx-os-http --help         (Show help)"
        echo "  dr-stynx-os-http --daemon        (Run in daemon mode)"
        echo "  dr-stynx-os-http --stop          (Stop server)"
    fi
    
    echo "======================================"
}

# Function to start the server
start_server() {
    local HOST="${1:-0.0.0.0}"
    local PORT="${2:-8080}"
    local STREAM_PORT="${3:-8081}"
    
    echo ""
    echo "Starting dr-stynx-os on:"
    echo "  📡 Host: $HOST"
    echo "  🔌 Port: $PORT (HTTP API)"
    echo "  🔌 Stream: $STREAM_PORT (WebSocket)"
    echo ""
    
    nohup python3 src/dr_stynx_os/http_server.py \
      --host "$HOST" \
      --port "$PORT" \
      --stream-port "$STREAM_PORT" \
      > /tmp/dr-stynx-os-$(date +%Y%m%d-%H%M%S).log 2>&1 &
    
    local pid=$!
    echo "Server PID: $pid"
    echo ""
    echo "📍 Server is now accessible at:"
    echo "   HTTP API:     http://$(hostname):$PORT/"
    echo "   WebSocket:    ws://$(hostname):$STREAM_PORT/"
    echo "======================================"
}

# Function to stop the server
stop_server() {
    echo ""
    echo "Stopping dr-stynx-os server..."
    pkill -f "dr-stynx-os-http"
    
    # Also kill any Python processes matching the pattern
    pkill -9 -f "src/dr_stynx_os/http_server.py" 2>/dev/null || true
    
    echo "✅ Server stopped"
    echo "======================================"
}

# Function to restart the server
restart_server() {
    stop_server
    sleep 1
    start_server "$@"
}

# Main menu
echo "Menu:"
echo "  start    - Start server (default ports: 8080, 8081)"
echo "  stop     - Stop the server"
echo "  restart  - Restart the server"
echo "  status   - Show current status"
echo "  help     - Show this help"
echo ""

case "${1:-status}" in
    start)
        HOST="${2:-0.0.0.0}"
        PORT="${3:-8080}"
        STREAM_PORT="${4:-8081}"
        start_server "$HOST" "$PORT" "$STREAM_PORT"
        ;;
    stop|restart)
        case "${1:-stop}" in
            stop) stop_server ;;
            restart) restart_server "$@" ;;
            *) stop_server ;;
        esac
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        echo "Usage: $0 {start|stop|restart|status} [options]"
        echo ""
        echo "Options (for start/restart):"
        echo "  --host HOST         Bind address (default: 0.0.0.0)"
        echo "  --port PORT         HTTP port (default: 8080)"
        echo "  --stream-port WS    WebSocket port (default: 8081)"
        echo ""
        show_status
        ;;
    *)
        # If called directly with arguments, execute those
        shift || true
        case "$1" in
            start|stop|restart) $1 "${@:-}" ;;
            status) show_status ;;
            *) 
                echo "Usage: $0 {start|stop|restart|status}"
                exit 1
                ;;
        esac
        ;;
esac

# Show final status
show_status
