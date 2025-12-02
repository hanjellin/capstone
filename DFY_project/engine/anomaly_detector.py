# engine/anomaly_detector.py

import json
import traceback
from pathlib import Path
from typing import Optional, Dict, Any

import torch

from model.dataset import FEATURE_KEYS
from model.ae_model import LoadAutoencoder
from engine import collector

# 전역 상태
_ae_detector: Optional["AEDetector"] = None
_ae_error_reason: Optional[str] = None


class AEDetector:
    """
    Autoencoder 기반 실시간 이상 탐지기.

    - 입력: 현재 시점의 metrics(dict)
    - 출력: reconstruction error + NORMAL/WARN/CRITICAL 상태
    """

    def __init__(self, model_path: Path, thresholds_path: Path, device: str = "cpu") -> None:
        self.device = device

        # 1) 임계값 / 통계 로드
        with thresholds_path.open("r", encoding="utf-8") as f:
            th = json.load(f)

        self.feature_keys = th.get("feature_keys", FEATURE_KEYS)
        self.feature_mean = torch.tensor(th["feature_mean"], dtype=torch.float32)
        self.feature_std = torch.tensor(th["feature_std"], dtype=torch.float32)
        self.error_mean = float(th["error_mean"])
        self.error_std = float(th["error_std"])
        self.warn_threshold = float(th["warn_threshold"])
        self.critical_threshold = float(th["critical_threshold"])
        self.num_samples = int(th.get("num_samples", 0))

        self.feature_std = torch.clamp(self.feature_std, min=1e-6)

        # 2) AE 모델 로드
        input_dim = len(self.feature_keys)
        self.model = LoadAutoencoder(
            input_dim=input_dim,
            hidden_dim=32,
            code_dim=8,
        ).to(self.device)

        state = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(state)
        self.model.eval()

    # ---- 내부 유틸 ----

    def _metrics_to_vector(self, metrics: Dict[str, Any]) -> torch.Tensor:
        """
        collector.get_current_metrics() 결과(dict)를 AE 입력 벡터로 변환.
        FEATURE_KEYS 순서를 그대로 사용한다.
        """
        def get_val(key: str) -> float:
            # AE 피처 이름 → collector 메트릭 이름 매핑
            mapping = {
                "cpu": "cpu_usage",
                "ram": "ram_usage",
                "gpu": "gpu_usage",
                "gpu_temp": "gpu_temp",
                "disk_read": "disk_read",
                "disk_write": "disk_write",
                "net_upload": "net_upload",
                "net_download": "net_download",
            }
            mkey = mapping.get(key, key)
            v = metrics.get(mkey, 0.0)
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        vec = [get_val(k) for k in self.feature_keys]
        x = torch.tensor(vec, dtype=torch.float32)
        return x

    def _compute_error(self, x: torch.Tensor) -> float:
        """
        단일 샘플 x (feature_dim,) 에 대한 reconstruction error 계산.
        """
        x_norm = (x - self.feature_mean) / self.feature_std
        x_norm = x_norm.to(self.device).unsqueeze(0)  # (1, F)

        with torch.no_grad():
            recon = self.model(x_norm)
            err = ((recon - x_norm) ** 2).mean().item()

        return float(err)

    # ---- 외부 인터페이스 ----

    def assess_current_state(self) -> Dict[str, Any]:
        """
        현재 collector의 실시간 metrics를 읽어와
        reconstruction error와 상태를 반환한다.
        """
        metrics = collector.get_current_metrics()
        x = self._metrics_to_vector(metrics)
        score = self._compute_error(x)

        if score >= self.critical_threshold:
            status = "CRITICAL"
        elif score >= self.warn_threshold:
            status = "WARN"
        else:
            status = "NORMAL"

        return {
            "status": status,
            "score": score,
            "warn_threshold": self.warn_threshold,
            "critical_threshold": self.critical_threshold,
            "error_mean": self.error_mean,
            "error_std": self.error_std,
            "num_samples": self.num_samples,
            "metrics": metrics,
        }


# ----------------------------------------------------------------------
# 전역 detector 관리
# ----------------------------------------------------------------------

def _init_detector_if_needed() -> Optional[AEDetector]:
    """
    모듈 전역으로 AEDetector를 lazy-init 한다.
    """
    global _ae_detector, _ae_error_reason

    if _ae_detector is not None:
        return _ae_detector

    root = Path(__file__).resolve().parents[1]
    model_path = root / "internal" / "model_autoencoder.pth"
    th_path = root / "internal" / "ae_thresholds.json"

    if not model_path.exists() or not th_path.exists():
        _ae_error_reason = f"AE 모델 또는 임계값 파일이 없습니다: {model_path.name}, {th_path.name}"
        print("[DFY][AE] Failed to initialize AEDetector:", _ae_error_reason)
        return None

    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _ae_detector = AEDetector(model_path, th_path, device=device)
        _ae_error_reason = None
        print("[DFY][AE] AEDetector initialized.")
        return _ae_detector
    except Exception as e:
        _ae_detector = None
        _ae_error_reason = str(e)
        print("[DFY][AE] Failed to initialize AEDetector:", e)
        traceback.print_exc()
        return None


def get_latest_anomaly() -> Dict[str, Any]:
    """
    UI에서 주기적으로 호출하는 함수.
    - 항상 dict 하나를 반환하도록 하고, 내부 에러는 여기서 처리.
    """
    global _ae_error_reason

    det = _init_detector_if_needed()
    if det is None:
        return {
            "status": "DISABLED",
            "reason": _ae_error_reason or "ae_not_available",
        }

    try:
        return det.assess_current_state()
    except Exception as e:
        _ae_error_reason = str(e)
        print("[DFY][AE] get_latest_anomaly() 내부 오류:", e)
        traceback.print_exc()
        return {
            "status": "ERROR",
            "reason": _ae_error_reason,
        }
