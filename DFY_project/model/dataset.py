# model/dataset.py
from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Tuple, Dict, Any, Iterable
import json
import glob
import torch
from torch.utils.data import Dataset, DataLoader

# Collector / Analyzer / Predictor에서 공통으로 쓰는 피처 목록
# 키 이름과 순서는 runtime 쪽(metrics_buffer, predictor 등)과 반드시 같아야 한다.
FEATURE_KEYS: List[str] = [
    "cpu",
    "ram",
    "gpu",
    "gpu_temp",
    "disk_read",
    "disk_write",
    "net_upload",
    "net_download",
]


def _find_column(fieldnames: List[str], patterns: Iterable[str]) -> str | None:
    """
    HWINFO CSV 헤더 목록(fieldnames)에서,
    주어진 패턴들 중 하나라도 포함하는 첫 번째 컬럼 이름을 찾아 반환한다.
    없으면 None.
    """
    for pattern in patterns:
        for name in fieldnames:
            if pattern in name:
                return name
    return None


def _build_column_map(fieldnames: List[str]) -> Dict[str, str | None]:
    """
    HWINFO 로그의 컬럼 이름을 LSTM에서 사용하는 FEATURE_KEYS로 매핑한다.

    가능한 한 유연하게 동작하도록, 정확한 이름 대신 부분 문자열 매칭을 사용한다.
    """
    colmap: Dict[str, str | None] = {}

    # CPU 전체 사용률
    colmap["cpu"] = _find_column(
        fieldnames,
        [
            "총 CPU 사용량",          # 한글 HWINFO
            "Total CPU Usage",
            "Total CPU",             # 영어 일반
        ],
    )

    # RAM 사용률 (Physical Memory Load)
    colmap["ram"] = _find_column(
        fieldnames,
        [
            "Physical Memory Load",
            "Memory Load [%]",
        ],
    )

    # GPU 사용률
    colmap["gpu"] = _find_column(
        fieldnames,
        [
            "GPU 활용률",
            "GPU Core Usage",
            "GPU Core Load",
            "GPU Usage",
        ],
    )

    # GPU 온도
    colmap["gpu_temp"] = _find_column(
        fieldnames,
        [
            "GPU 온도",
            "GPU Temperature",
        ],
    )

    # 디스크 읽기/쓰기 속도 (MB/s 기준)
    colmap["disk_read"] = _find_column(
        fieldnames,
        [
            "Read Rate [MB/s]",
            "Read Rate [KB/s]",
        ],
    )
    colmap["disk_write"] = _find_column(
        fieldnames,
        [
            "Write Rate [MB/s]",
            "Write Rate [KB/s]",
        ],
    )

    # 네트워크 DL/UP 속도 (각 어댑터의 Current rate – KB/s 기준인 경우가 많음)
    colmap["net_download"] = _find_column(
        fieldnames,
        [
            "Current DL rate",
            "Download Rate",
        ],
    )
    colmap["net_upload"] = _find_column(
        fieldnames,
        [
            "Current UP rate",
            "Upload Rate",
        ],
    )

    return colmap


class LoadDataset(Dataset):
    """
    data/daily/report_*.json 을 읽어서
    (seq_len, feature_dim) -> target_cpu 형태로 만드는 Dataset.

    - JSON 인코딩이 UTF-8 / CP949 뒤섞여 있어도 최대한 대응.
    - JSON이 아닌 파일(실제로는 CSV인데 .json으로 저장된 것 등)은 자동으로 스킵.
    - 실제 데이터에서 나온 시계열만 사용하고,
      아무 샘플도 없으면 그냥 빈 Dataset으로 둔다.
    """

    def __init__(self, daily_dir: str = "data/daily", seq_len: int = 30) -> None:
        self.seq_len = seq_len
        # samples: List[(x_tensor, y_tensor)]
        self.samples: List[Tuple[torch.Tensor, torch.Tensor]] = []

        daily_path = Path(daily_dir)
        json_files = sorted(glob.glob(str(daily_path / "report_*.json")))

        for jf in json_files:
            report = None

            # 1) UTF-8로 먼저 시도
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    report = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # 2) 안 되면 CP949(EUC-KR)로 재시도
                try:
                    with open(jf, "r", encoding="cp949") as f:
                        report = json.load(f)
                except Exception as e:
                    print(f"[DFY][dataset][WARN] JSON/인코딩 오류, 파일 스킵: {jf} ({e})")
                    continue

            # report 형태 확인
            if not isinstance(report, (list, dict)):
                print(f"[DFY][dataset][WARN] 예상치 못한 JSON 구조, 파일 스킵: {jf}")
                continue

            # 시계열 추출
            series = self._extract_series(report)
            if not series or len(series) <= seq_len:
                continue

            # 시계열 → 슬라이딩 윈도우 샘플 생성
            self._add_series_samples(series)

        # 실제 데이터로 만든 샘플이 하나도 없을 때
        if not self.samples:
            print("[DFY][dataset][WARN] data/daily 에서 학습에 쓸 샘플을 찾지 못했습니다.")
            print("[DFY][dataset][WARN] Autoencoder/LSTM은 실제 데이터가 쌓인 뒤에야 학습할 수 있습니다.")
        else:
            print(f"[DFY][dataset] 총 샘플 수: {len(self.samples)} (윈도우 길이={self.seq_len})")

    # ---------------- 내부 메서드들 ----------------

    def _extract_series(self, report: Any) -> List[Dict[str, Any]]:
        """
        report 구조가 어떻게 생겼든 간에, 가능한 한
        'cpu'를 포함한 dict들의 리스트를 찾아서 반환한다.
        """

        # case 1: report 자체가 리스트인 경우
        if isinstance(report, list):
            # 리스트 첫 원소가 dict이고 'cpu'를 가지면 바로 사용
            if report and isinstance(report[0], dict) and "cpu" in report[0]:
                return report

            # 리스트 안에 또 다른 구조들이 섞여 있으면 재귀적으로 탐색
            for item in report:
                sub = self._extract_series(item)
                if sub:
                    return sub
            return []

        # case 2: dict인 경우 – 여러 키 후보를 순서대로 검사
        if isinstance(report, dict):
            # 가장 흔하게 쓰일 법한 키들
            candidate_keys = [
                "time_series",
                "samples",
                "data",
                "history",
                "series",
                "metrics",
                "records",
            ]
            for key in candidate_keys:
                if key in report:
                    v = report[key]
                    if isinstance(v, list) and v:
                        if isinstance(v[0], dict) and "cpu" in v[0]:
                            return v

            # 위에서 못 찾았으면 dict 내부 값들을 재귀적으로 훑기
            for v in report.values():
                sub = self._extract_series(v)
                if sub:
                    return sub

            # 최후의 수단: dict 자신이 시점 하나일 수 있음
            if "cpu" in report:
                return [report]

        # 그 외 타입은 시계열 정보가 아니라고 판단
        return []

    def _add_series_samples(self, series: List[Dict[str, Any]]) -> None:
        """
        시계열 series(각 원소가 dict)를 받아서
        슬라이딩 윈도우로 (x_seq, target_cpu) 샘플들을 self.samples에 추가한다.

        - x_seq      : (seq_len, feature_dim)
        - target_cpu : 다음 시점의 CPU 사용량 (스칼라)
        """
        if len(series) <= self.seq_len:
            return

        for i in range(len(series) - self.seq_len):
            # 입력 seq_len + 타겟 1 (총 seq_len+1 길이의 윈도우)
            window = series[i : i + self.seq_len + 1]

            # cpu가 없는 시점이 섞여 있으면 스킵
            valid = True
            for step in window:
                if "cpu" not in step:
                    valid = False
                    break
            if not valid:
                continue

            # 입력 시퀀스 x_seq
            x_seq: List[List[float]] = []
            for step in window[:-1]:
                vec: List[float] = []
                for k in FEATURE_KEYS:
                    v = step.get(k, 0.0)
                    try:
                        v = float(v) if v is not None else 0.0
                    except (TypeError, ValueError):
                        v = 0.0
                    vec.append(v)
                x_seq.append(vec)

            # 타겟: 마지막 시점의 cpu
            target_cpu = window[-1].get("cpu", 0.0)
            try:
                target_cpu_f = float(target_cpu)
            except (TypeError, ValueError):
                continue

            x_tensor = torch.tensor(x_seq, dtype=torch.float32)
            y_tensor = torch.tensor([target_cpu_f], dtype=torch.float32)
            self.samples.append((x_tensor, y_tensor))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        return self.samples[idx]


def create_dataloader(
    daily_dir: str = "data/daily",
    seq_len: int = 30,
    batch_size: int = 64,
    shuffle: bool = True,
):
    """
    LoadDataset으로부터 DataLoader를 만든다.

    - 실제 샘플이 하나도 없으면(None 반환):
        * Autoencoder/LSTM 학습 쪽에서 그냥 '데이터 없음' 처리하고 종료하도록.
    """
    dataset = LoadDataset(daily_dir=daily_dir, seq_len=seq_len)

    if len(dataset) == 0:
        print("[DFY][dataset][WARN] Empty dataset, DataLoader를 생성하지 않습니다.")
        return None

    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)