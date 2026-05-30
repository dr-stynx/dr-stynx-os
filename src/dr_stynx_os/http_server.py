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

class JSONRPC2Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[JSON-RPC HTTP] {format % args}")
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        origin = self.headers.get('Origin', '*')
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def _send_error(self, status, error_response):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(error_response).encode())
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'
        
        if path == '/health':
            state = load_state()
            self._send_json({"status": "ok", "heartbeat_count": state.get("heartbeat_count", 0)})
        
        elif path == '/gpu' or path == '/gpu/status':
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
                
                self._send_json({"gpus": gpus, "count": len(gpus)})
            except Exception as e:
                self._send_error(400, {"jsonrpc": "2.0", "error": {"code": -32600, "message": str(e)}, "id": None})
        
        elif path == '/state':
            state = load_state()
            self._send_json(state)
        
        elif path == '/tasks':
            state = load_state()
            self._send_json({"tasks": state.get("tasks", []), "count": len(state.get("tasks", []))})
        
        elif path == '/heartbeat':
            import time
            state = load_state()
            state["heartbeat_count"] = state.get("heartbeat_count", 0) + 1
            state["last_heartbeat"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_state(state)
            self._send_json({"status": "healthy", "heartbeat_count": state["heartbeat_count"], "last_heartbeat": state.get("last_heartbeat")})
        
        else:
            self._send_error(404, {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": None})
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        if path == '/tasks' or path == '/task':
            if 'description' in data and 'priority' in data:
                state = load_state()
                if "tasks" not in state:
                    state["tasks"] = []
                
                task = {
                    "id": len(state.get("tasks", [])) + 1,
                    "description": data['description'],
                    "priority": data['priority'],
                    "status": "pending",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                state["tasks"].append(task)
                save_state(state)
                
                self._send_json({"task_id": task["id"], "message": f"Task added: {data['description']}"})
            else:
                self._send_error(400, {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Invalid request parameters"}, "id": None})
        
        elif path == '/heartbeat':
            import time
            state = load_state()
            state["heartbeat_count"] = state.get("heartbeat_count", 0) + 1
            state["last_heartbeat"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_state(state)
            
            self._send_json({"status": "healthy", "heartbeat_count": state["heartbeat_count"], "last_heartbeat": state.get("last_heartbeat")})
        
        else:
            self._send_error(404, {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": None})
    
    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'
        
        if path == '/tasks' or path == '/task/clear':
            state = load_state()
            state["tasks"] = []
            save_state(state)
            self._send_json({"message": "All tasks cleared"})
        
        else:
            self._send_error(404, {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": None})

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
    parser.add_argument('--port', type=int, default=8111, help='HTTP port (default: 8111)')
    parser.add_argument('--stream-port', type=int, default=8222, help='WebSocket streaming port (default: 8222)')
    
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

if __name__ == "__main__":
    main()
