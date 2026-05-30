import subprocess
from typing import List, Dict, Any

def get_gpu_stats() -> List[Dict[str, Any]]:
    """Get GPU stats by parsing nvidia-smi output"""
    stats = []
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,index,temperature.gpu,memory.total,memory.used,utilization.gpu,processes.pid,processes.name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode != 0:
            return [{"error": f"nvidia-smi failed: {result.stderr}"}]
        
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                stats.append({
                    "id": parts[0],
                    "name": parts[1],
                    "temp_c": int(parts[2]),
                    "mem_total_mb": float(parts[3].replace("MiB", "").strip()),
                    "mem_used_mb": float(parts[4].replace("MiB", "").strip()),
                    "gpu_util_percent": float(parts[5].rstrip("%")),
                    "pid": [],
                    "name_list": parts[6] if len(parts) > 6 else []
                })
            elif len(parts) >= 2:
                stats.append({
                    "id": parts[0],
                    "name": parts[1],
                    "temp_c": int(parts[2]) if len(parts) > 2 else 0,
                    "mem_total_mb": float(parts[3].replace("MiB", "").strip()) if len(parts) > 3 else 0,
                    "mem_used_mb": float(parts[4].replace("MiB", "").strip()) if len(parts) > 4 else 0,
                    "gpu_util_percent": float(parts[5].rstrip("%")) if len(parts) > 5 else 0,
                    "pid": [],
                    "name_list": parts[6:] if len(parts) > 6 else []
                })
                
    except Exception as e:
        stats.append({"error": str(e)})
    
    return stats

def shutdown_gpu():
    """Shutdown GPU (not recommended - would need nvidia-smi --gpu-reset)"""
    pass
