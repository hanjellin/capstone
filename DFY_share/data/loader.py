# data/loader.py
import platform
import psutil
import GPUtil

def get_os_info():
    return {
        "name": platform.system(),
        "version": platform.version(),
        "release": platform.release(),
        "machine": platform.machine()
    }

def get_cpu_info():
    return {
        "model": platform.processor(),
        "cores_physical": psutil.cpu_count(logical=False),
        "cores_logical": psutil.cpu_count(logical=True),
        "usage_percent": psutil.cpu_percent(interval=0.1)
    }

def get_ram_info():
    ram = psutil.virtual_memory()
    return {
        "total_gb": round(ram.total / (1024**3), 2),
        "used_gb": round(ram.used / (1024**3), 2),
        "percent": ram.percent
    }

def get_gpu_info():
    try:
        gpus = GPUtil.getGPUs()
        if not gpus:
            return {"gpu": "None"}

        gpu = gpus[0]
        return {
            "name": gpu.name,
            "vram_total_gb": round(gpu.memoryTotal / 1024, 2),
            "vram_used_gb": round(gpu.memoryUsed / 1024, 2),
            "temperature": gpu.temperature
        }
    except:
        return {"gpu": "Not Supported"}

def get_disk_info():
    disks = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "percent": usage.percent
            })
        except:
            continue
    return disks

def get_network_info():
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()

    result = {}

    for name, addr_list in addrs.items():
        if name in stats and stats[name].isup:
            ip = None
            for a in addr_list:
                if a.family == 2:  # IPv4
                    ip = a.address
            result[name] = {
                "ip": ip,
                "speed": stats[name].speed
            }

    return result

# -----------------------------------------------------

def collect_specs():
    """ 전체 PC 정보를 JSON(dict)로 반환 """
    return {
        "os": get_os_info(),
        "cpu": get_cpu_info(),
        "ram": get_ram_info(),
        "gpu": get_gpu_info(),
        "disk": get_disk_info(),
        "network": get_network_info()
    }
