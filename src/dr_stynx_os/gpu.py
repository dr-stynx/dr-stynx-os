import pynvml
from typing import List, Dict, Any

def init_gpu():
    pynvml.nvmlInit()

def get_gpu_stats() -> List[Dict[str, Any]]:
    stats = []
    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            usage = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            stats.append({
                "id": i,
                "name": name,
                "temp_c": temp,
                "gpu_util_percent": usage.gpu,
                "mem_used_mb": mem.used / 1024**2,
                "mem_total_mb": mem.total / 1024**2
            })
    except Exception as e:
        stats.append({"error": str(e)})
    return stats

def shutdown_gpu():
    try:
        pynvml.nvmlShutdown()
    except:
        pass
