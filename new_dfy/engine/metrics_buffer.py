import time

_MAX_SAMPLES = 600  # 대략 10분이라고 가정 (1초 간격)

_buffer = []  # {"timestamp":..., "cpu_temp":..., "cpu_usage":..., "features": {...}}


def add_sample(metrics: dict):
    """collector.get_current_metrics() 결과를 버퍼에 기록"""
    sample = {
        "timestamp": time.time(),
        "cpu_temp": metrics.get("cpu_temp"),
        "gpu_temp": metrics.get("gpu_temp"),
        "cpu_usage": metrics.get("cpu_usage"),
        "ram_usage": metrics.get("ram_usage"),
    }

    cpu = metrics.get("cpu_usage") or 0.0
    ram = metrics.get("ram_usage") or 0.0
    gpu = metrics.get("gpu_usage") or 0.0
    gpu_temp = metrics.get("gpu_temp") or 0.0

    # model.dataset.FEATURE_KEYS 형식
    feature_snap = {
        "cpu": float(cpu),
        "ram": float(ram),
        "gpu": float(gpu),
        "gpu_temp": float(gpu_temp),
        "disk_read": 0.0,
        "disk_write": 0.0,
        "net_upload": 0.0,
        "net_download": 0.0,
    }
    sample["features"] = feature_snap

    _buffer.append(sample)
    if len(_buffer) > _MAX_SAMPLES:
        del _buffer[0: len(_buffer) - _MAX_SAMPLES]


def get_series(key: str):
    return [s[key] for s in _buffer if s.get(key) is not None]


def get_all():
    return list(_buffer)


def get_feature_history(limit: int | None = None):
    hist = [s["features"] for s in _buffer if "features" in s]
    if limit is not None and len(hist) > limit:
        hist = hist[-limit:]
    return hist
