# model/dataset.py
import glob
import json
import math
import random
from pathlib import Path
from typing import List, Tuple, Dict, Any

import torch
from torch.utils.data import Dataset, DataLoader


# Collector / Analyzer / Predictor에서 공통으로 쓰는 피처 목록
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


class LoadDataset(Dataset):
    """
    data/daily/report_*.json 을 읽어서
    (seq_len, feature_dim) -> target_cpu 형태로 만드는 Dataset.
    - JSON 구조가 조금 달라도 웬만하면 알아서 시계열을 찾아 쓴다.
    - 아무 데이터도 없으면 synthetic(가짜) 데이터로 모델 학습이 가능하도록 만든다.
    """

    def __init__(self, daily_dir: str = "data/daily", seq_len: int = 30) -> None:
        self.seq_len = seq_len
        self.samples: List[Tuple[torch.Tensor, torch.Tensor]] = []

        daily_path = Path(daily_dir)
        json_files = sorted(glob.glob(str(daily_path / "report_*.json")))

        for jf in json_files:
            with open(jf, "r", encoding="utf-8") as f:
                try:
                    report = json.load(f)
                except json.JSONDecodeError:
                    continue

            series = self._extract_series(report)
            if not series or len(series) <= seq_len:
                continue

            self._add_series_samples(series)

        # 진짜 데이터로 만든 샘플이 하나도 없으면 synthetic 데이터 생성
        if not self.samples:
            print("[DFY][WARN] data/daily 에서 학습에 쓸 샘플을 찾지 못했습니다.")
            print("[DFY][WARN] synthetic(가짜) 데이터를 생성해서 기본 모델을 학습합니다.")
            self._create_synthetic_samples(num_series=200, length=120)

    # ---------------- 내부 메서드들 ----------------

    def _extract_series(self, report: Any) -> List[Dict[str, Any]]:
        """
        report 구조가 어떻게 생겼든 간에, 가능한 한
        'cpu'를 포함한 dict들의 리스트를 찾아서 반환한다.
        """

        # case 1: report 자체가 리스트인 경우
        if isinstance(report, list):
            if report and isinstance(report[0], dict) and "cpu" in report[0]:
                return report

        # case 2: dict인 경우 – 여러 키 후보를 순서대로 검사
        if isinstance(report, dict):
            # 가장 흔하게 쓰일 법한 키들
            candidate_keys = [
                "time_series",
                "samples",
                "data",
                "history",
                "records",
                "snapshots",
            ]
            for key in candidate_keys:
                v = report.get(key)
                if isinstance(v, list) and v:
                    if isinstance(v[0], dict) and "cpu" in v[0]:
                        return v

            # case 3: dict 안의 value들 중에서 리스트인 것들 검사
            for v in report.values():
                if isinstance(v, list) and v:
                    if isinstance(v[0], dict) and "cpu" in v[0]:
                        return v

        # 적절한 리스트를 못 찾으면 빈 리스트
        return []

    def _add_series_samples(self, series: List[Dict[str, Any]]) -> None:
        """
        하나의 시계열 리스트(series)를 받아서
        슬라이딩 윈도우로 (x_seq, y_cpu) 샘플들을 self.samples에 추가.
        """
        if len(series) <= self.seq_len:
            return

        for i in range(len(series) - self.seq_len):
            window = series[i : i + self.seq_len + 1]  # 입력 seq_len + 타겟 1

            # cpu가 없는 시점이 섞여 있으면 스킵
            valid = True
            for step in window:
                if "cpu" not in step:
                    valid = False
                    break
            if not valid:
                continue

            x_seq = []
            for step in window[:-1]:
                vec = []
                for k in FEATURE_KEYS:
                    v = step.get(k, 0.0)
                    try:
                        v = float(v) if v is not None else 0.0
                    except (TypeError, ValueError):
                        v = 0.0
                    vec.append(v)
                x_seq.append(vec)

            target_cpu = window[-1].get("cpu", 0.0)
            try:
                target_cpu = float(target_cpu)
            except (TypeError, ValueError):
                continue

            x_tensor = torch.tensor(x_seq, dtype=torch.float32)
            y_tensor = torch.tensor([target_cpu], dtype=torch.float32)
            self.samples.append((x_tensor, y_tensor))

    def _create_synthetic_samples(
        self,
        num_series: int = 200,
        length: int = 120,
    ) -> None:
        """
        진짜 데이터가 하나도 없을 때, 기본 모델 학습용 synthetic 데이터 생성.
        - CPU, RAM, GPU 등의 값을 적당한 패턴으로 만들어서
          "그럴듯한" 시계열을 구성한다.
        """
        for _ in range(num_series):
            base_cpu = random.uniform(10, 40)  # 기본 부하
            base_ram = random.uniform(30, 60)
            series: List[Dict[str, float]] = []

            for t in range(length):
                # 시간에 따라 조금씩 변동 + 가끔 스파이크
                spike = 0.0
                if random.random() < 0.05:  # 5% 확률로 스파이크
                    spike = random.uniform(20, 40)

                cpu = max(0.0, min(100.0, base_cpu + math.sin(t / 5) * 5 + spike))
                ram = max(0.0, min(100.0, base_ram + math.sin(t / 7) * 3 + spike * 0.3))
                gpu = max(0.0, min(100.0, cpu * random.uniform(0.3, 0.8)))
                gpu_temp = 30 + gpu * 0.6 + random.uniform(-3, 3)

                disk_read = max(0.0, random.gauss(2.0, 1.0))
                disk_write = max(0.0, random.gauss(2.0, 1.0))
                net_up = max(0.0, random.gauss(5.0, 2.0))
                net_down = max(0.0, random.gauss(8.0, 3.0))

                series.append(
                    {
                        "cpu": cpu,
                        "ram": ram,
                        "gpu": gpu,
                        "gpu_temp": gpu_temp,
                        "disk_read": disk_read,
                        "disk_write": disk_write,
                        "net_upload": net_up,
                        "net_download": net_down,
                    }
                )

            self._add_series_samples(series)

        if not self.samples:
            raise RuntimeError("synthetic 데이터 생성에도 실패했습니다. 코드 로직을 확인하세요.")

    # ---------------- Dataset 인터페이스 ----------------

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        return self.samples[idx]


def create_dataloader(
    daily_dir: str = "data/daily",
    seq_len: int = 30,
    batch_size: int = 64,
    shuffle: bool = True,
) -> DataLoader:
    dataset = LoadDataset(daily_dir=daily_dir, seq_len=seq_len)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)
