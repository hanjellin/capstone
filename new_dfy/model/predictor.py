# model/predictor.py
from __future__ import annotations

import math
from pathlib import Path
from typing import List, Dict, Any, Optional

import torch

from model.lstm_model import LoadLSTM
from model.dataset import FEATURE_KEYS


class LoadPredictor:
    """
    DFY Assistant용 부하 예측기.
    최근 seq_len개의 snapshot 리스트를 받아
    - 다음 시점의 CPU 사용률 예측
    - 위험도(0~1), 상태 문자열 반환
    """

    def __init__(
        self,
        model_path: str = "internal/model_load_lstm.pth",
        seq_len: int = 30,
        device: Optional[str] = None,
    ) -> None:
        self.seq_len = seq_len
        self.model_path = Path(model_path)

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"모델 가중치 파일이 없습니다: {self.model_path}\n"
                f"먼저 `python -m model.train_lstm` 를 실행해 학습을 완료하세요."
            )

        self.model = LoadLSTM(input_dim=len(FEATURE_KEYS))
        state = torch.load(self.model_path, map_location=self.device)
        self.model.load_state_dict(state)
        self.model.to(self.device)
        self.model.eval()

    def _build_sequence(self, history: List[Dict[str, Any]]) -> torch.Tensor:
        """
        history: 최근 N개의 snapshot (SystemCollector.get_data() 포맷)
        """
        if len(history) < self.seq_len:
            pad_needed = self.seq_len - len(history)
            padding = [history[0]] * pad_needed if history else [{
                k: 0.0 for k in FEATURE_KEYS
            }]
            history = padding + history

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
    def predict_next_cpu(self, history: List[Dict[str, Any]]) -> float:
        x = self._build_sequence(history)
        pred = self.model(x)   # (1, 1)
        return float(pred.item())

    @torch.no_grad()
    def assess_risk(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        history[-1]['cpu'] 와 예측된 cpu_next 를 비교해서 위험도 계산.
        """
        if not history:
            return {
                "status": "UNKNOWN",
                "risk_score": 0.0,
                "predicted_cpu": None,
                "current_cpu": None,
                "reason": "no history",
            }

        current_cpu = float(history[-1].get("cpu", 0.0))
        pred_cpu = self.predict_next_cpu(history)

        # 기준: 75% 이상이면 위험 커짐, 그 이상일수록 risk_score ↑
        # (pred_cpu - 75) / 7.5 를 sigmoid에 넣어서 0~1 스케일
        z = (pred_cpu - 75.0) / 7.5
        risk_raw = 1 / (1 + math.exp(-z))
        risk_score = max(0.0, min(1.0, risk_raw))

        if risk_score < 0.33:
            status = "NORMAL"
        elif risk_score < 0.66:
            status = "WARN"
        else:
            status = "CRITICAL"

        return {
            "status": status,
            "risk_score": risk_score,
            "predicted_cpu": pred_cpu,
            "current_cpu": current_cpu,
        }
