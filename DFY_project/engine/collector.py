# engine/collector.py
import platform
import os
import time
from pathlib import Path

import psutil

try:
    import GPUtil  # GPU 정보용
except ImportError:
    GPUtil = None

# ---------- 내부 상태 (디스크/네트워크 속도 계산용) ----------

_last_disk_io = None
_last_net_io = None
_last_io_time = None


# ---------- 시스템 스펙 (UI 사양 탭에서 사용) ----------

def get_system_specs():
    """
    시스템 고정 스펙 정보 (CPU / RAM / 디스크 / GPU).
    psutil + GPUtil만 사용, HWiNFO와는 완전히 독립.
    """
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

    # 디스크 (에러 나는 파티션은 건너뜀)
    disk_info = []
    for part in psutil.disk_partitions(all=False):
        mount = part.mountpoint
        if not mount:
            continue
        try:
            usage = psutil.disk_usage(mount)
        except (PermissionError, FileNotFoundError, OSError, SystemError):
            continue

        disk_info.append({
            "device": part.device,
            "mountpoint": mount,
            "fstype": part.fstype,
            "total_gb": usage.total / (1024 ** 3),
            "used_gb": usage.used / (1024 ** 3),
            "percent": usage.percent,
        })

    # GPU (가능하면)
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


# ---------- 내부: 센서 읽기 도우미 ----------

def _get_cpu_temp_psutil():
    """psutil로 CPU 온도 하나 가져오기 (안 되면 None)."""
    if not hasattr(psutil, "sensors_temperatures"):
        return None
    try:
        temps = psutil.sensors_temperatures()
    except Exception:
        return None
    if not temps:
        return None

    # 가장 먼저 보이는 센서 하나 집어옴
    for _, entries in temps.items():
        if entries:
            try:
                return float(entries[0].current)
            except Exception:
                continue
    return None


def _get_gpu_temp_psutil():
    """GPUtil로 GPU 온도 하나 가져오기 (안 되면 None)."""
    if GPUtil is None:
        return None
    try:
        gpus = GPUtil.getGPUs()
    except Exception:
        return None
    if not gpus:
        return None
    return float(gpus[0].temperature)


def _get_gpu_usage_psutil():
    """GPUtil로 GPU 사용률 하나 가져오기 (안 되면 None)."""
    if GPUtil is None:
        return None
    try:
        gpus = GPUtil.getGPUs()
    except Exception:
        return None
    if not gpus:
        return None
    return float(gpus[0].load * 100.0)


def _get_disk_net_rates():
    """
    디스크/네트워크 속도를 MB/s 단위로 근사 계산.
    이전 호출과의 차이로 계산하며, 최초 호출 시에는 0으로 리턴.
    """
    global _last_disk_io, _last_net_io, _last_io_time

    now = time.time()
    try:
        disk = psutil.disk_io_counters()
        net = psutil.net_io_counters()
    except Exception:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    if _last_disk_io is None or _last_net_io is None or _last_io_time is None:
        _last_disk_io = disk
        _last_net_io = net
        _last_io_time = now
        # 처음에는 속도를 0으로 반환
        return 0.0, 0.0, 0.0, 0.0, net.bytes_sent / (1024 ** 2), net.bytes_recv / (1024 ** 2)

    dt = now - _last_io_time
    if dt <= 0:
        dt = 1.0

    # 초당 바이트 → MB/s
    disk_read_mb_s = (disk.read_bytes - _last_disk_io.read_bytes) / (1024 ** 2 * dt)
    disk_write_mb_s = (disk.write_bytes - _last_disk_io.write_bytes) / (1024 ** 2 * dt)
    net_up_mb_s = (net.bytes_sent - _last_net_io.bytes_sent) / (1024 ** 2 * dt)
    net_down_mb_s = (net.bytes_recv - _last_net_io.bytes_recv) / (1024 ** 2 * dt)

    # 누적 송수신량 (MB)
    net_sent_mb = net.bytes_sent / (1024 ** 2)
    net_recv_mb = net.bytes_recv / (1024 ** 2)

    _last_disk_io = disk
    _last_net_io = net
    _last_io_time = now

    return disk_read_mb_s, disk_write_mb_s, net_up_mb_s, net_down_mb_s, net_sent_mb, net_recv_mb


# ---------- 실시간 상태 (모니터링/대시보드/엔진에서 사용) ----------

def get_current_metrics():
    """
    실시간 모니터링용 현재 상태.

    - cpu_usage      : psutil.cpu_percent()
    - ram_usage      : psutil.virtual_memory().percent
    - disk_usage     : 시스템 드라이브(C:) 사용률 %
    - disk_read      : 디스크 읽기 속도 (MB/s)
    - disk_write     : 디스크 쓰기 속도 (MB/s)
    - net_upload     : 업로드 속도 (MB/s)
    - net_download   : 다운로드 속도 (MB/s)
    - net_sent_mb    : 지금까지 보낸 누적 데이터 (MB)
    - net_recv_mb    : 지금까지 받은 누적 데이터 (MB)
    - cpu_temp       : psutil.sensors_temperatures() (지원 안 되면 None)
    - gpu_temp       : GPUtil GPU 온도 (없으면 None)
    - gpu_usage      : GPUtil GPU 사용률 (없으면 None)
    """

    # CPU / RAM
    cpu_usage = psutil.cpu_percent(interval=None)
    vm = psutil.virtual_memory()
    ram_usage = vm.percent

    # 디스크 사용률 (시스템 드라이브 기준)
    try:
        system_drive = os.getenv("SystemDrive", "C:") + "\\"
        d = psutil.disk_usage(system_drive)
        disk_usage = d.percent
    except Exception:
        disk_usage = 0.0

    # 디스크 / 네트워크 속도 & 누적치
    disk_read_mb_s, disk_write_mb_s, net_up_mb_s, net_down_mb_s, net_sent_mb, net_recv_mb = _get_disk_net_rates()

    # 온도 / GPU 사용률
    cpu_temp = _get_cpu_temp_psutil()
    gpu_temp = _get_gpu_temp_psutil()
    gpu_usage = _get_gpu_usage_psutil()

    metrics = {
        "cpu_usage": cpu_usage,
        "ram_usage": ram_usage,
        "disk_usage": disk_usage,
        "disk_read": disk_read_mb_s,
        "disk_write": disk_write_mb_s,
        "net_upload": net_up_mb_s,
        "net_download": net_down_mb_s,
        "net_sent_mb": net_sent_mb,
        "net_recv_mb": net_recv_mb,
        "cpu_temp": cpu_temp,
        "gpu_temp": gpu_temp,
        "gpu_usage": gpu_usage,
    }

    return metrics
