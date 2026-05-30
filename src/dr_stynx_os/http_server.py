#!/usr/bin/env python3
"""
Dr. Stynx OS HTTP/JSON-RPC Server with WebSocket Streaming Support
Exposes GPU monitoring and task management as JSON-RPC endpoints for Metatron integration.
"""
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import threading
import asyncio
import websockets
import time

STATE_FILE = os.path.expanduser("~/.dr-stynx-state.json")
STREAM_PORT = 8081
JSONRPC_PORT = 8080

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"status": "idle", "tasks": [], "heartbeat_count": 0}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def load_tasks():
    state = load_state()
    return state.get("tasks", [])

def add_task(description, priority="low"):
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
    return task

def clear_tasks():
    state = load_state()
    state["tasks"] = []
    save_state(state)

class JSONRPC2Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[JSON-RPC HTTP] {format % args}")
    
    def do_POST(self):
        parsed = urlparse(self.path)
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
        
        try:
            rpc = json.loads(body) if body else {"jsonrpc": "2.0", "method": "", "params": {}}
        except:
            rpc = {"jsonrpc": "2.0", "method": "", "params": {}, "id": None}
        
        # Validate JSON-RPC 2.0 structure
        if "jsonrpc" not in rpc or rpc["jsonrpc"] != "2.0":
            self._send_error(400, {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Invalid JSON-RPC Version"}, "id": rpc.get("id")})
            return
        
        method = rpc.get("method", "")
        params = rpc.get("params", {})
        notification = isinstance(rpc.get('notification'), bool) or rpc.get('method') == '' and not 'jsonrpc' in rpc
        request_id = rpc.get("id") if not notification else None
        
        try:
            # Route JSON-RPC method calls
            if method == "health":
                state = load_state()
                result = {"status": "ok", "heartbeat_count": state.get("heartbeat_count", 0), "version": "1.0.0"}
            
            elif method == "gpu.status":
                import subprocess
                try:
                    result = subprocess.run(
                        ["nvidia-smi", "--query-gpu=name,index,temperature.gpu,memory.total,memory.used,utilization.gpu", "--format=csv,noheader"],
                        capture_output=True, text=True, timeout=5
                    )
                    gpus = []
                    for line in [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]:
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) >= 6:
                            gpus.append({
                                "id": int(parts[0]),
                                "name": parts[1],
                                "temp_c": int(parts[2]),
                                "mem_total_mb": float(parts[3].replace("MiB", "").strip()) or 0,
                                "mem_used_mb": float(parts[4].replace("MiB", "").strip()) or 0,
                                "gpu_util_percent": float(parts[5].rstrip("%")) or 0
                            })
                    result = {"gpus": gpus, "count": len(gpus)}
                except Exception as e:
                    result = {"error": str(e)}
            
            elif method == "state.get":
                result = load_state()
            
            elif method in ["task.add", "tasks.add"]:
                if not isinstance(params, dict):
                    params = {}
                description = params.get("description") or params.get("d")
                priority = params.get("priority", "low") or params.get("p")
                
                if description:
                    task = add_task(description, priority)
                    result = {"id": task["id"], "status": "success", "message": f"Task added: {description}"}
                else:
                    result = {"error": "Missing description parameter"}
            
            elif method in ["task.clear", "tasks.clear"]:
                clear_tasks()
                result = {"id": None, "status": "success", "message": "All tasks cleared"}
            
            elif method == "heartbeat":
                state = load_state()
                state["heartbeat_count"] = state.get("heartbeat_count", 0) + 1
                state["last_heartbeat"] = time.strftime("%Y-%m-%d %H:%M:%S")
                state["status"] = "active"
                save_state(state)
                result = {
                    "id": None,
                    "status": "ok", 
                    "heartbeat_count": state["heartbeat_count"],
                    "last_heartbeat": state.get("last_heartbeat"),
                    "timestamp": time.time()
                }
            
            elif method == "task.list" or method == "tasks.list":
                tasks = load_tasks()
                result = {"tasks": tasks, "count": len(tasks)}
            
            else:
                result = {"error": f"Unknown method: {method}", "supported_methods": ["health", "gpu.status", "state.get", "task.add", "task.clear", "heartbeat", "task.list"]}
            
            # Send JSON-RPC response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            if request_id is not None:
                response = {"jsonrpc": "2.0", "result": result, "id": request_id}
            else:
                response = {"jsonrpc": "2.0", "result": result}
            
            self.wfile.write(json.dumps(response).encode())
        
        except json.JSONDecodeError as e:
            self._send_error(400, {"jsonrpc": "2.0", "error": {"code": -32701, "message": "Invalid Request", "data": f"JSON decode error: {str(e)}"}, "id": request_id})
        except Exception as e:
            self._send_error(500, {"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal Error", "data": str(e)}, "id": request_id})
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/health':
            state = load_state()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"jsonrpc": "2.0", "result": {"status": "ok", "heartbeat_count": state.get("heartbeat_count", 0), "version": "1.0.0"}, "id": 1}
            self.wfile.write(json.dumps(response).encode())
        
        elif parsed.path == '/info':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            response = (
                "Dr. Stynx OS JSON-RPC Server v1.0.0\n"
                "=======================================\n"
                "Supported Methods:\n"
                "  health - Check server status\n"
                "  gpu.status - Get GPU stats\n"
                "  state.get - Get internal state\n"
                "  task.add <desc> <priority> - Add a task\n"
                "  task.clear - Clear all tasks\n"
                "  heartbeat - Self-awareness ping\n"
                "  task.list - List all tasks\n"
            )
            self.wfile.write(response.encode())
        
        else:
            self.send_response(404)
            self.end_headers()

class WebSocketStreamingServer:
    """WebSocket server for streaming GPU updates and state changes"""
    
    def __init__(self, host='localhost', port=8081):
        self.host = host
        self.port = port
        self.connected_clients = set()
    
    async def broadcast(self, message):
        """Broadcast message to all connected clients"""
        if self.connected_clients:
            await asyncio.gather(
                *[client.send(json.dumps(message)) for client in list(self.connected_clients)],
                return_exceptions=True
            )
    
    async def start(self):
        """Start WebSocket streaming server"""
        async def handle_websocket(websocket, path):
            self.connected_clients.add(websocket)
            print(f"🔌 WebSocket client connected")
            
            try:
                async for message in websocket:
                    if isinstance(message, str):
                        rpc = json.loads(message)
                        
                        method = rpc.get("method", "")
                        
                        # Handle subscription notifications
                        if method == "subscribe.gpu":
                            await self.broadcast({
                                "jsonrpc": "2.0",
                                "notification": True,
                                "method": "gpu.update",
                                "result": {"status": "subscribed"}
                            })
                        
                        elif method == "unsubscribe.gpu":
                            # Stop broadcasting (would need more state management)
                            pass
                        
                        await self.broadcast({
                            "jsonrpc": "2.0",
                            "notification": True,
                            "method": "heartbeat.ping"
                        })
                        
                    elif isinstance(message, bytes):
                        try:
                            rpc = json.loads(message.decode())
                            method = rpc.get("method", "")
                            
                            if method == "unsubscribe.gpu":
                                pass  # Would handle unsubscribe
                            
                        except json.JSONDecodeError:
                            continue
            finally:
                self.connected_clients.discard(websocket)
            
        async def start_server():
            async with websockets.serve(
                handle_websocket, 
                self.host, 
                self.port
            ) as ws:
                print(f"🔌 Dr. Stynx OS WebSocket Streaming on {self.host}:{self.port}")
                await asyncio.Future()  # run forever
        
        threading.Thread(target=asyncio.run, args=(start_server(),), daemon=True).start()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Dr. Stynx OS Server")
    parser.add_argument('--host', default='localhost', help='Host to bind')
    parser.add_argument('--port', type=int, default=8080, help='HTTP port (default: 8080)')
    parser.add_argument('--stream-port', type=int, default=8081, help='WebSocket streaming port (default: 8081)')
    
    args = parser.parse_args()
    
    # Start JSON-RPC HTTP server in a thread
    threading.Thread(
        target=lambda: HTTPServer((args.host, args.port), JSONRPC2Handler).serve_forever(),
        daemon=True
    ).start()
    
    # Start WebSocket streaming server
    ws_server = WebSocketStreamingServer(args.host, args.stream_port)
    ws_thread = threading.Thread(target=ws_server.start, daemon=True)
    ws_thread.start()
    
    print(f"🚀 Dr. Stynx OS Server starting...")
    print(f"   📡 JSON-RPC HTTP: {args.host}:{args.port}")
    print(f"   🔌 WebSocket Stream: {args.host}:{args.stream_port}")
    print(f"\nSupported JSON-RPC Methods:")
    print("   POST health - Get server health")
    print("   POST gpu.status - Get GPU stats (parsing nvidia-smi)")
    print("   POST state.get - Get internal state")
    print("   POST task.add <description> [priority] - Add a task")
    print("   POST task.clear - Clear all tasks")
    print("   POST heartbeat - Trigger self-awareness")
    print("   POST task.list - List all tasks")
    print("\nHTTP Request Format (JSON-RPC 2.0):")
    print(json.dumps({
        "jsonrpc": "2.0",
        "method": "gpu.status",
        "params": {},
        "id": None
    }, indent=2))
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Dr. Stynx OS Server stopped")

if __name__ == "__main__":
    main()