#!/usr/bin/env python3
"""Test script for Dr. Stynx OS JSON-RPC HTTP Server"""
import json
import urllib.request
import sys

BASE_URL = "http://localhost:8111"

def make_request(method, params=None):
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": None
    }).encode()
    
    req = urllib.request.Request(
        f"{BASE_URL}/",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_all():
    print("🧪 Testing Dr. Stynx OS HTTP/JSON-RPC Server\n")
    
    # Test health
    print("1️⃣  Health check...")
    result = make_request("health")
    if result and "status" in result:
        print(f"   ✅ {json.dumps(result, indent=4)}")
    else:
        print("   ❌ Failed")
    
    # Test state.get
    print("\n2️⃣  Get state...")
    result = make_request("state.get")
    if result:
        print(f"   ✅ {json.dumps(result, indent=4)}")
    else:
        print("   ❌ Failed")
    
    # Test task.add
    print("\n3️⃣  Add task...")
    result = make_request("task.add", {"description": "test gpu monitoring for metatron", "priority": "high"})
    if result and "id" in result:
        print(f"   ✅ Task #{result['id']} created!")
    else:
        print("   ❌ Failed")
    
    # Test task.list
    print("\n4️⃣  List tasks...")
    result = make_request("task.list")
    if result and "tasks" in result:
        print(f"   ✅ Found {len(result['tasks'])} tasks:")
        for t in result['tasks']:
            print(f"      - #{t['id']}: {t['description']} [{t['priority']}]")
    else:
        print("   ❌ Failed")
    
    # Test heartbeat
    print("\n5️⃣  Heartbeat...")
    result = make_request("heartbeat")
    if result and "heartbeat_count" in result:
        print(f"   ✅ Heartbeat #{result['heartbeat_count']} at {result.get('last_heartbeat', 'N/A')}")
    else:
        print("   ❌ Failed")
    
    # Test GPU status (may fail if nvidia-smi not available)
    print("\n6️⃣  GPU status...")
    result = make_request("gpu.status")
    if result:
        if "error" in result:
            print(f"   ⚠️  {result['error']} (may need nvidia-smi)")
        elif "gpus" in result:
            print(f"   ✅ Found {len(result['gpus'])} GPU(s):")
            for g in result['gpus']:
                print(f"      - {g['name']}: {g['temp_c']}°C, {g['gpu_util_percent']}% util")
        else:
            print(f"   ✅ Response: {json.dumps(result[:200])}...")
    else:
        print("   ❌ Failed")
    
    # Test task.clear
    print("\n7️⃣  Clear tasks...")
    result = make_request("task.clear")
    if result and result.get("status") == "success":
        print("   ✅ All tasks cleared!")
    else:
        print("   ❌ Failed")
    
    # Final health check
    print("\n8️⃣  Final health check...")
    result = make_request("health")
    if result and result.get("status") == "ok":
        print(f"   ✅ Server healthy! (heartbeat_count: {result.get('heartbeat_count', 0)})")
    else:
        print("   ❌ Not healthy")
    
    return True

if __name__ == "__main__":
    test_all()
    print("\n🧪 Test complete!")
