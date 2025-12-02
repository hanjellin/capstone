# engine/metrics_buffer.py
import time
from typing import Dict, Any, List, Optional

# LSTM이 사용하는 피처 키 목록을 공유해서, 순서/이름 불일치를 막는다.
try:
    from model.dataset import FEATURE_KEYS
except ImportError:
    # 모델 쪽이 아직 없을 때를 대비한 기본값 (실제 실행 시에는 model.dataset 쪽이 우선)
    FEATURE_KEYS = [
        "cpu",
        "ram",
        "gpu",
        "gpu_temp",
        "disk_read",
        "disk_write",
        "net_upload",
        "net_download",
    ]

_MAX_SAMPLES = 600  # 대략 10분 분량(1초 간격)이라고 가정

# 각 원소 예시:
# {
#     "timestamp": 1710000000.0,
#     "cpu_temp": 55.0,
#     "gpu_temp": 60.0,
#     "cpu_usage": 35.0,
#     "ram_usage": 60.0,
#     "disk_usage": 40.0,
#     "gpu_usage": 10.0,
#     "features": {
#         "cpu": ...,
#         "ram": ...,
#         ...
#     }
# }
_buffer: List[Dict[str, Any]] = []


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def add_sample(metrics: Dict[str, Any]) -> None:
    """
    collector.get_current_metrics() 결과를 버퍼에 기록하고,
    LSTM 입력용 feature 벡터도 같이 저장한다.
    """
    # 기본 메타 정보
    sample: Dict[str, Any] = {
        "timestamp": time.time(),
        "cpu_temp": metrics.get("cpu_temp"),
        "gpu_temp": metrics.get("gpu_temp"),
        "cpu_usage": metrics.get("cpu_usage"),
        "ram_usage": metrics.get("ram_usage"),
        "disk_usage": metrics.get("disk_usage"),
        "gpu_usage": metrics.get("gpu_usage"),
    }

    # LSTM이 기대하는 8개 피처를 collector 값에서 매핑
    # (collector.get_current_metrics() 의 키와 맞춰야 한다)
    cpu = metrics.get("cpu_usage")
    ram = metrics.get("ram_usage")
    gpu = metrics.get("gpu_usage")
    gpu_temp = metrics.get("gpu_temp")

    disk_read = metrics.get("disk_read")       # MB/s
    disk_write = metrics.get("disk_write")     # MB/s
    net_up = metrics.get("net_upload")         # MB/s
    net_down = metrics.get("net_download")     # MB/s

    feature_snap: Dict[str, float] = {
        "cpu": _safe_float(cpu),
        "ram": _safe_float(ram),
        "gpu": _safe_float(gpu),
        "gpu_temp": _safe_float(gpu_temp),
        "disk_read": _safe_float(disk_read),
        "disk_write": _safe_float(disk_write),
        "net_upload": _safe_float(net_up),
        "net_download": _safe_float(net_down),
    }

    # 혹시 FEATURE_KEYS가 달라졌을 때도 순서/필터를 맞춰주기 위해 다시 정리
    ordered_features = {k: feature_snap.get(k, 0.0) for k in FEATURE_KEYS}

    sample["features"] = ordered_features

    _buffer.append(sample)

    # 오래된 샘플은 버린다
    if len(_buffer) > _MAX_SAMPLES:
        del _buffer[0]


def clear() -> None:
    """버퍼를 완전히 비운다 (테스트용)."""
    _buffer.clear()


def get_series(key: str) -> List[float]:
    """
    buffer에서 특정 키(cpu_usage, cpu_temp 등)의 시계열만 뽑아서 반환.
    None 값은 제외.
    """
    return [s[key] for s in _buffer if s.get(key) is not None]


def get_all() -> List[Dict[str, Any]]:
    """버퍼 전체를 shallow copy로 반환."""
    return list(_buffer)


def get_feature_history(limit: Optional[int] = None) -> List[Dict[str, float]]:
    """
    LSTM 입력용 feature history를 반환.

    각 원소는 {feature_name: value} dict이고,
    limit가 주어지면 뒤에서부터 해당 개수만큼만 잘라서 반환.
    """
    hist = [s["features"] for s in _buffer if "features" in s]
    if limit is not None and len(hist) > limit:
        hist = hist[-limit:]
    return hist
