# model/ae_detector.py
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import torch

from model.ae_model import LoadAutoencoder
from model.dataset import FEATURE_KEYS
from engine import collector

class AEDetector:
    """
    Autoencoder 기반 시계열 이상 탐지기.

    - 입력: 최근 history (metrics_buffer.get_feature_history() 포맷)
    - 출력:
        * compute_score() : Reconstruction Error 스칼라
        * classify()      : NORMAL / WARN / CRITICAL 분류 + score/thresholds
    """

    def __init__(
        self,
        model_path: str = "internal/model_autoencoder.pth",
        threshold_path: str = "internal/ae_thresholds.json",
        seq_len: int = 30,
        device: Optional[str] = None,
    ) -> None:
        self.seq_len = seq_len
        self.model_path = Path(model_path)
        self.threshold_path = Path(threshold_path)

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        # --- 모델 로드 ---
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"AE 모델 가중치 파일이 없습니다: {self.model_path}\n"
                f"먼저 'python -m model.train_ae' 로 Autoencoder를 학습해 주세요."
            )

        self.model = LoadAutoencoder(
            seq_len=self.seq_len,
            input_dim=len(FEATURE_KEYS),
        )
        state = torch.load(self.model_path, map_location=self.device)
        self.model.load_state_dict(state)
        self.model.to(self.device)
        self.model.eval()

        # --- 임계값 로드 ---
        self.thresholds = self._load_thresholds()

    def _load_thresholds(self) -> Dict[str, float]:
        """
        train_ae.py에서 저장한 ae_thresholds.json 로드.
        없으면 0 기반 기본값 반환.
        """
        if not self.threshold_path.exists():
            # 기본값 (임계값 없으면 그냥 0으로 세팅)
            return {
                "mean": 0.0,
                "std": 0.0,
                "warn": 0.0,
                "critical": 0.0,
            }

        with self.threshold_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        out: Dict[str, float] = {}
        for k in ("mean", "std", "warn", "critical"):
            v = data.get(k, 0.0)
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                out[k] = 0.0
        return out

    def _build_sequence(self, history: List[Dict[str, Any]]) -> Optional[torch.Tensor]:
        """
        history: 최근 N개의 snapshot
                 예) metrics_buffer.get_feature_history() 결과

        반환: (1, seq_len, dim) 텐서 (device로 옮겨진 상태)
        """
        if not history:
            return None

        # 길이가 모자라면 앞쪽을 복제해서 패딩
        if len(history) < self.seq_len:
            pad_needed = self.seq_len - len(history)
            padding = [history[0]] * pad_needed
            history = padding + history

        # 너무 길면 뒤에서 seq_len개만 사용
        history = history[-self.seq_len :]

        seq = []
        for snap in history:
            vec = []
            for k in FEATURE_KEYS:
                v = snap.get(k, 0.0)
                try:
                    v = float(v) if v is not None else 0.0
                except (TypeError, ValueError):
                    v = 0.0
                vec.append(v)
            seq.append(vec)

        x = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)  # (1, seq_len, dim)
        return x.to(self.device)

    @torch.no_grad()
    def compute_score(self, history: List[Dict[str, Any]]) -> Optional[float]:
        """
        Reconstruction Error (MSE)를 스칼라로 반환.
        history가 비어 있으면 None.
        """
        x = self._build_sequence(history)
        if x is None:
            return None

        # reconstruction_error(reduction="none") → (batch,)
        scores = self.model.reconstruction_error(x, reduction="none")
        return float(scores.item())

    @torch.no_grad()
    def classify(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        history 기반 Reconstruction Error를 계산하고,
        warn / critical 임계값에 따라 상태를 분류한다.

        반환 예:
        {
            "status": "NORMAL" / "WARN" / "CRITICAL" / "UNKNOWN",
            "score":  0.0032 또는 None,
            "thresholds": { "mean":..., "std":..., "warn":..., "critical":... },
            "reason": "no history"  # 필요 시
        }
        """
        score = self.compute_score(history)

        if score is None:
            return {
                "status": "UNKNOWN",
                "score": None,
                "thresholds": self.thresholds,
                "reason": "no history",
            }

        warn = self.thresholds.get("warn", 0.0)
        critical = self.thresholds.get("critical", warn)

        if critical <= warn:
            # 임계값이 비정상적으로 설정된 경우 → 일단 NORMAL로 간주
            status = "NORMAL"
        else:
            if score < warn:
                status = "NORMAL"
            elif score < critical:
                status = "WARN"
            else:
                status = "CRITICAL"

        return {
            "status": status,
            "score": score,
            "thresholds": self.thresholds,
        }
        
    def assess_current_state(self) -> Dict[str, Any]:
        """
            현재 collector의 실시간 metrics를 읽어와
            reconstruction error와 상태를 반환한다.
        추가로, 어떤 항목이 평소와 가장 다르게 튀었는지도 함께 돌려준다.
        """
        metrics = collector.get_current_metrics()
        x = self._metrics_to_vector(metrics)

        # 🔻 새 헬퍼로 전체 score + 상위 편차 피처 계산
        score, top_devs = self._analyze_deviation(x, metrics)

        # 상태 판정
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
            # 🔻 새 필드: 어떤 피처가 얼마나 튀는지에 대한 정보
            "top_deviations": top_devs,
        }

        # 🔻 새로 추가: 피처별 편차(평균 대비)와 에러를 계산해서 상위 몇 개만 뽑아주는 함수
    def _analyze_deviation(
        self,
        x: torch.Tensor,
        metrics: Dict[str, Any],
    ):
        """
        x: (feature_dim,)  현재 시점의 원본 피처 벡터
        metrics: collector.get_current_metrics() 결과 딕셔너리

        반환:
            score: 전체 reconstruction error (float)
            top_devs: 이상도가 큰 피처 상위 몇 개 리스트
        """
        # 학습 때와 같은 방식으로 정규화
        x_norm = (x - self.feature_mean) / self.feature_std
        x_norm_batch = x_norm.to(self.device).unsqueeze(0)  # (1, F)

        with torch.no_grad():
            recon = self.model(x_norm_batch)
            err_vec = ((recon - x_norm_batch) ** 2)[0]  # (F,)
            score = float(err_vec.mean().item())

        # z-score 는 x_norm 값 자체가 됨
        z_vec = x_norm  # (F,)
    def assess_current_state(self) -> Dict[str, Any]:
        """
        현재 collector의 실시간 metrics를 읽어와
        reconstruction error와 상태를 반환한다.
        추가로, 어떤 항목이 평소와 가장 다르게 튀었는지도 함께 돌려준다.
        """
        metrics = collector.get_current_metrics()
        x = self._metrics_to_vector(metrics)

        # 🔻 새 헬퍼로 전체 score + 상위 편차 피처 계산
        score, top_devs = self._analyze_deviation(x, metrics)

        # 상태 판정
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
            # 🔻 새 필드: 어떤 피처가 얼마나 튀는지에 대한 정보
            "top_deviations": top_devs,
        }

        # 피처 키 → collector 메트릭 키 매핑 (metrics에서 실제 값 꺼낼 때 사용)
        key_to_metric = {
            "cpu": "cpu_usage",
            "ram": "ram_usage",
            "gpu": "gpu_usage",
            "gpu_temp": "gpu_temp",
            "disk_read": "disk_read",
            "disk_write": "disk_write",
            "net_upload": "net_upload",
            "net_download": "net_download",
        }

        # 사용자에게 보여줄 한글 라벨
        nice_labels = {
            "cpu": "CPU 사용률",
            "ram": "RAM 사용률",
            "gpu": "GPU 사용률",
            "gpu_temp": "GPU 온도",
            "disk_read": "디스크 읽기 속도",
            "disk_write": "디스크 쓰기 속도",
            "net_upload": "업로드 속도",
            "net_download": "다운로드 속도",
        }

        deviations = []
        for idx, key in enumerate(self.feature_keys):
            z = float(z_vec[idx].item())
            err = float(err_vec[idx].item())

            # 현재 실제 값 (예: CPU 사용률 %)도 같이 넣어두면 나중에 쓸 수 있음
            mkey = key_to_metric.get(key, key)
            raw_val = metrics.get(mkey, 0.0)
            try:
                raw_val = float(raw_val)
            except (TypeError, ValueError):
                raw_val = 0.0

            # 방향: 높은 쪽으로 튐 / 낮은 쪽으로 튐 / 애매
            if z >= 0.5:
                direction = "high"
            elif z <= -0.5:
                direction = "low"
            else:
                direction = "neutral"

            deviations.append(
                {
                    "key": key,
                    "label": nice_labels.get(key, key),
                    "z": z,
                    "error": err,
                    "direction": direction,
                    "value": raw_val,
                }
            )

        # 절댓값 z-score가 큰 순으로 정렬
        deviations.sort(key=lambda d: abs(d["z"]), reverse=True)

        # 너무 애매한 건 버리고(|z|>=1.0 이상만) 상위 3개만 사용
        top_devs = [d for d in deviations if abs(d["z"]) >= 1.0][:3]

        return score, top_devs
