import platform
import os

import psutil

try:
    import GPUtil
except ImportError:
    GPUtil = None


def get_system_specs():
    """시스템 고정 스펙 정보"""
    uname = platform.uname()

    # CPU
    cpu_name = uname.processor or platform.processor()
    cpu_count_physical = psutil.cpu_count(logical=False) or 0
    cpu_count_logical = psutil.cpu_count(logical=True) or 0
    freq = psutil.cpu_freq()
    cpu_base_freq = freq.max or (freq.current if freq else 0.0)

    # RAM
    vm = psutil.virtual_memory()
    ram_total_gb = vm.total / (1024 ** 3)

    # 디스크
    disk_info = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue
        disk_info.append({
            "device": part.device,
            "mountpoint": part.mountpoint,
            "fstype": part.fstype,
            "total_gb": usage.total / (1024 ** 3),
            "used_gb": usage.used / (1024 ** 3),
            "percent": usage.percent,
        })

    # GPU
    gpus = []
    if GPUtil is not None:
        try:
            for gpu in GPUtil.getGPUs():
                gpus.append({
                    "name": gpu.name,
                    "memory_total_mb": gpu.memoryTotal,
                    "memory_used_mb": gpu.memoryUsed,
                    "load": gpu.load * 100.0,
                    "temperature": gpu.temperature,
                })
        except Exception:
            pass

    return {
        "os": {
            "system": uname.system,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "node": uname.node,
        },
        "cpu": {
            "name": cpu_name,
            "physical_cores": cpu_count_physical,
            "logical_cores": cpu_count_logical,
            "base_freq_mhz": cpu_base_freq,
        },
        "ram": {
            "total_gb": ram_total_gb,
        },
        "disks": disk_info,
        "gpus": gpus,
    }


def _get_any_cpu_temp():
    if not hasattr(psutil, "sensors_temperatures"):
        return None
    try:
        temps = psutil.sensors_temperatures()
    except Exception:
        return None
    if not temps:
        return None
    for _, entries in temps.items():
        if entries:
            return entries[0].current
    return None


def _get_any_gpu_temp():
    if GPUtil is None:
        return None
    try:
        gpus = GPUtil.getGPUs()
    except Exception:
        return None
    if not gpus:
        return None
    return gpus[0].temperature


def _get_any_gpu_usage():
    if GPUtil is None:
        return None
    try:
        gpus = GPUtil.getGPUs()
    except Exception:
        return None
    if not gpus:
        return None
    return gpus[0].load * 100.0


def get_current_metrics():
    """실시간 모니터링용 현재 상태"""
    cpu_usage = psutil.cpu_percent(interval=None)
    vm = psutil.virtual_memory()
    ram_usage = vm.percent

    disk_usage = None
    try:
        system_drive = os.getenv("SystemDrive", "C:") + "\\"
        d = psutil.disk_usage(system_drive)
        disk_usage = d.percent
    except Exception:
        pass

    net_io = psutil.net_io_counters()
    net_sent_mb = net_io.bytes_sent / (1024 ** 2)
    net_recv_mb = net_io.bytes_recv / (1024 ** 2)

    cpu_temp = _get_any_cpu_temp()
    gpu_temp = _get_any_gpu_temp()
    gpu_usage = _get_any_gpu_usage()

    return {
        "cpu_usage": cpu_usage,
        "ram_usage": ram_usage,
        "disk_usage": disk_usage,
        "net_sent_mb": net_sent_mb,
        "net_recv_mb": net_recv_mb,
        "cpu_temp": cpu_temp,
        "gpu_temp": gpu_temp,
        "gpu_usage": gpu_usage,
    }
