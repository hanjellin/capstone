# model/train_ae.py
import csv
import json
from pathlib import Path
from typing import List, Dict, Optional
import torch
from torch import nn
from torch.utils.data import TensorDataset, DataLoader
from model.ae_model import LoadAutoencoder

# 기존 LSTM/Predictor와 동일한 피처 순서 사용
from model.dataset import FEATURE_KEYS  # ["cpu","ram","gpu","gpu_temp","disk_read","disk_write","net_upload","net_download"]

# HWiNFO 로그 경로 (collector에서 쓰는 것과 맞춰 주세요)
HWINF0_LOG_PATH = Path("data/daily/time_log.CSV")


# ---------------------------------------------------------------------------
# Autoencoder 모델 정의
# ---------------------------------------------------------------------------

class SimpleAE(nn.Module):
    """
    한 시점의 피처 벡터 (len(FEATURE_KEYS) 차원)를 입력으로 받는
    간단한 완전연결 Autoencoder.
    """

    def __init__(self, input_dim: int, hidden_dim: int = 32, code_dim: int = 8):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, code_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(code_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.encoder(x)
        out = self.decoder(z)
        return out


# ---------------------------------------------------------------------------
# HWiNFO CSV → 학습용 피처 행렬로 변환
# ---------------------------------------------------------------------------

def _find_column(fieldnames: List[str], patterns: List[str]) -> Optional[str]:
    """여러 후보 문자열 중에서 header 안에 들어있는 이름을 찾아서 반환."""
    for p in patterns:
        for name in fieldnames:
            if p in name:
                return name
    return None


def _build_column_map(fieldnames: List[str]) -> Dict[str, str]:
    """
    HWiNFO header에서 우리가 쓸 컬럼 이름들을 찾아 매핑한다.
    (이름이 약간 달라도 패턴 포함 여부로 찾도록 설계)
    """
    colmap: Dict[str, str] = {}

    colmap["cpu"] = _find_column(fieldnames, ["총 CPU 사용량", "Total CPU Usage"])
    colmap["ram"] = _find_column(fieldnames, ["Physical Memory Load", "메모리 사용량"])
    colmap["gpu"] = _find_column(fieldnames, ["GPU 활용률", "GPU Core Usage", "GPU Usage"])
    colmap["gpu_temp"] = _find_column(fieldnames, ["GPU 온도", "GPU Temperature"])
    colmap["disk_read"] = _find_column(fieldnames, ["Read Rate [MB/s]", "Read Rate [KB/s]"])
    colmap["disk_write"] = _find_column(fieldnames, ["Write Rate [MB/s]", "Write Rate [KB/s]"])
    colmap["net_download"] = _find_column(fieldnames, ["Current DL rate", "Download Rate"])
    colmap["net_upload"] = _find_column(fieldnames, ["Current UP rate", "Upload Rate"])

    return colmap


def _parse_float(raw: str) -> Optional[float]:
    """문자열을 float로 바꾸되, 실패하면 None."""
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "":
        return None
    # , 를 . 로 바꿔서 유럽식 소수점도 방어
    raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None

def load_hwinfo_features_from_csv(csv_path: Path) -> torch.Tensor:
    """
    HWiNFO time_log.CSV에서 FEATURE_KEYS 순서대로 값만 뽑아
    (num_samples, feature_dim) 텐서를 만들어 반환.

    - 파일 인코딩이 깨져 있어도 상관없이, utf-8-sig + errors="ignore" 로 강제 디코딩.
    - 우리는 숫자 컬럼만 사용하므로, 본문 중간의 한글 텍스트가 깨지더라도 문제 없음.
    """
    if not csv_path.is_absolute():
        root = Path(__file__).resolve().parents[1]
        csv_path = root / csv_path

    if not csv_path.exists():
        raise FileNotFoundError(f"HWiNFO 로그 파일을 찾을 수 없습니다: {csv_path}")

    print(f"[DFY][AE] HWiNFO CSV 읽는 중: {csv_path}")

    features_list: List[List[float]] = []

    # ✅ 인코딩이 섞여 있어도 강제로 읽는다 (잘못된 바이트는 버림)
    with csv_path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise RuntimeError("CSV header(fieldnames)를 읽지 못했습니다.")

        colmap = _build_column_map(reader.fieldnames)
        print("[DFY][AE] Column mapping:")
        for k in FEATURE_KEYS:
            print(f"   {k:<12} <- {colmap.get(k)}")

        for row in reader:
            vec: List[float] = []
            skip_row = False
            for key in FEATURE_KEYS:
                colname = colmap.get(key)
                if not colname:
                    # 해당 피처를 못 찾으면 그 자리는 0으로 채움
                    val = 0.0
                else:
                    val = _parse_float(row.get(colname))
                    if val is None:
                        # CPU / RAM 같이 핵심 피처가 None이면 행 자체를 버리는 게 낫다
                        if key in ("cpu", "ram"):
                            skip_row = True
                            break
                        val = 0.0

                    # 네트워크는 KB/s → MB/s 변환 (헤더에 KB/s 라벨이 있는 경우)
                    if key in ("net_download", "net_upload") and "KB/s" in colname:
                        val /= 1024.0

                    # 디스크도 KB/s 인 경우가 있으면 MB/s 로 변환
                    if key in ("disk_read", "disk_write") and "KB/s" in colname:
                        val /= 1024.0

                vec.append(float(val))

            if skip_row:
                continue
            features_list.append(vec)

    if not features_list:
        raise RuntimeError("CSV에서 유효한 피처 행을 하나도 찾지 못했습니다.")

    X = torch.tensor(features_list, dtype=torch.float32)
    print(f"[DFY][AE] 로드된 샘플 수: {X.shape[0]}, feature_dim: {X.shape[1]}")
    return X

# ---------------------------------------------------------------------------
# 학습 메인 루틴
# ---------------------------------------------------------------------------

def train_ae(
    csv_rel_path: Path | str = HWINF0_LOG_PATH,
    batch_size: int = 256,
    epochs: int = 15,
    lr: float = 1e-3,
):
    """
    HWiNFO CSV(time_log.CSV)에서 직접 피처를 읽어와 Autoencoder를 학습한다.
    - Reconstruction Error 분포로부터 WARN / CRITICAL 임계값도 계산하여 저장한다.
    """
    root = Path(__file__).resolve().parents[1]
    model_dir = root / "internal"
    model_dir.mkdir(parents=True, exist_ok=True)

    # 1) 데이터 로드
    try:
        X = load_hwinfo_features_from_csv(Path(csv_rel_path))
    except Exception as e:
        print(f"[DFY][AE][ERROR] CSV 로드 실패: {e}")
        return

    num_samples, feature_dim = X.shape
    if num_samples < 100:
        print("[DFY][AE][WARN] 샘플 수가 너무 적어 Autoencoder 학습이 어렵습니다.")
        return

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[DFY][AE] Training Autoencoder on {device} | samples={num_samples}, dim={feature_dim}")

    # 2) 표준화 (feature-wise mean/std)
    feat_mean = X.mean(dim=0)
    feat_std = X.std(dim=0)
    feat_std_clamped = torch.clamp(feat_std, min=1e-6)

    X_norm = (X - feat_mean) / feat_std_clamped

    dataset = TensorDataset(X_norm)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # 3) 모델 / 옵티마이저 설정
        # AE 모델 생성 (ae_model.LoadAutoencoder 사용)
    model = LoadAutoencoder(
        input_dim=feature_dim,
        hidden_dim=32,
        code_dim=8,
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    # 4) 학습 루프
    model.train()
    for epoch in range(1, epochs + 1):
        epoch_loss = 0.0
        n = 0
        for (batch_x,) in dataloader:
            batch_x = batch_x.to(device)

            optimizer.zero_grad()
            recon = model(batch_x)
            loss = criterion(recon, batch_x)
            loss.backward()
            optimizer.step()

            batch_size_actual = batch_x.size(0)
            epoch_loss += loss.item() * batch_size_actual
            n += batch_size_actual

        avg_loss = epoch_loss / max(n, 1)
        print(f"[DFY][AE][Epoch {epoch}/{epochs}] MSE: {avg_loss:.6f}")

    # 5) 모델 저장 (state_dict)
    model_path = model_dir / "model_autoencoder.pth"
    torch.save(model.state_dict(), model_path)
    print(f"[DFY][AE] Autoencoder 모델 저장: {model_path}")

    # 6) 학습 데이터에 대한 Reconstruction Error 분포 계산 → 임계값 설정
    model.eval()
    with torch.no_grad():
        X_norm_device = X_norm.to(device)
        recon = model(X_norm_device)
        # 각 샘플별 평균 제곱오차
        errors = ((recon - X_norm_device) ** 2).mean(dim=1).cpu()

    err_mean = float(errors.mean().item())
    err_std = float(errors.std(unbiased=False).item())
    if err_std < 1e-9:
        err_std = 1e-9

    warn_threshold = err_mean + 2.0 * err_std
    critical_threshold = err_mean + 4.0 * err_std

    thresholds = {
        "feature_keys": FEATURE_KEYS,
        "feature_mean": feat_mean.tolist(),
        "feature_std": feat_std_clamped.tolist(),
        "error_mean": err_mean,
        "error_std": err_std,
        "warn_threshold": warn_threshold,
        "critical_threshold": critical_threshold,
        "num_samples": int(num_samples),
    }

    th_path = model_dir / "ae_thresholds.json"
    with th_path.open("w", encoding="utf-8") as f:
        json.dump(thresholds, f, indent=2, ensure_ascii=False)

    print("[DFY][AE] Thresholds 저장:")
    print(f"   mean error      : {err_mean:.6f}")
    print(f"   warn threshold  : {warn_threshold:.6f}")
    print(f"   critical thres. : {critical_threshold:.6f}")
    print(f"   file            : {th_path}")
    print("[DFY][AE] Autoencoder 학습이 완료되었습니다.")


if __name__ == "__main__":
    train_ae()
