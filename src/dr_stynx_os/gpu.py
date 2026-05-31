import requests
import json
from typing import List, Dict, Any

GLANCES_API_URL = "https://glances.phaseshift.studio/api/4/gpu"

def get_gpu_stats() -> List[Dict[str, Any]]:
    """Get GPU stats from Glances REST API"""
    stats = []
    try:
        response = requests.get(GLANCES_API_URL, timeout=5)
        response.raise_for_status()
        
        gpu_data = response.json()
        if not isinstance(gpu_data, list):
            return [{"error": "Unexpected GPU data format"}]
        
        for gpu in gpu_data:
            stats.append({
                "id": gpu.get("gpu_id", "unknown"),
                "name": gpu.get("name", "Unknown GPU"),
                "temp_c": gpu.get("temperature", 0),
                "mem_total_mb": None,  # Glances v4 doesn't provide total memory
                "mem_used_mb": None,   # Glances v4 provides percentage instead
                "mem_used_percent": gpu.get("mem", 0),
                "gpu_util_percent": gpu.get("proc", 0),
                "fan_speed": gpu.get("fan_speed"),
                "pid": [],
                "name_list": []
            })
            
    except requests.exceptions.Timeout:
        stats.append({"error": "Glances API timeout"})
    except requests.exceptions.ConnectionError:
        stats.append({"error": "Cannot connect to Glances API"})
    except Exception as e:
        stats.append({"error": str(e)})
    
    return stats

def shutdown_gpu():
    """Shutdown GPU (not recommended)"""
    pass
