# main.py
from __future__ import annotations

import random
from pathlib import Path

from model.dataset import LoadDataset, FEATURE_KEYS
from model.train_lstm import train
from model.predictor import LoadPredictor


# ==== 설정 ====
CSV_PATH = "data/daily/log.CSV"   # 네가 쓰는 HWINFO 로그 위치
SEQ_LEN = 30
BATCH_SIZE = 64
NUM_EPOCHS = 3                    # 테스트용이니까 짧게, 실제 학습은 늘리면 됨
MODEL_PATH = "internal/model_load_lstm.pth"


def inspect_random_sample(dataset: LoadDataset) -> None:
    """데이터셋에서 임의의 샘플 하나를 뽑아서 내용 확인."""
    idx = random.randrange(len(dataset))
    x, y = dataset[idx]

    print(f"\n[1] 데이터셋 확인")
    print(f"- 전체 샘플 수: {len(dataset)}")
    print(f"- 선택된 인덱스: {idx}")
    print(f"- x shape: {x.shape} (seq_len, feature_dim)")
    print(f"- y (다음 시점 cpu): {y.item():.4f}")

    # 마지막 타임스텝만 출력
    print("\n  마지막 타임스텝 feature 값:")
    last_step = x[-1].tolist()
    for key, val in zip(FEATURE_KEYS, last_step):
        print(f"    {key:>12s}: {val:.4f}")


def history_from_sample(x_tensor) -> list[dict]:
    """
    데이터셋에서 뽑은 x (seq_len, feature_dim)를
    predictor가 기대하는 history 형식(list[dict])으로 변환.
    """
    history: list[dict] = []
    for row in x_tensor:
        row_list = row.tolist()
        snap = {k: float(v) for k, v in zip(FEATURE_KEYS, row_list)}
        history.append(snap)
    return history


def main() -> None:
    root = Path(__file__).resolve().parent
    print(f"[DFY_TEST] 프로젝트 루트: {root}")

    # 1. 데이터셋 로딩 및 샘플 확인
    dataset = LoadDataset(daily_dir=CSV_PATH, seq_len=SEQ_LEN)
    inspect_random_sample(dataset)

    # 2. LSTM 짧게 학습 (테스트용)
    print("\n[2] LSTM 학습 시작 (테스트용)")
    train(
        daily_dir=CSV_PATH,
        seq_len=SEQ_LEN,
        batch_size=BATCH_SIZE,
        num_epochs=NUM_EPOCHS,
        save_path=MODEL_PATH,   # train_lstm 쪽에서 프로젝트 루트 기준으로 처리하는 걸 추천
    )
    print("[2] LSTM 학습 완료")

    # 3. Predictor 로드 및 예측 테스트
    print("\n[3] Predictor 로드 및 예측 테스트")

    predictor = LoadPredictor(
        model_path=MODEL_PATH,
        seq_len=SEQ_LEN,
    )

    # 데이터셋의 마지막 샘플로 history 구성
    x_last, y_last = dataset[len(dataset) - 1]
    history = history_from_sample(x_last)

    pred_cpu = predictor.predict_next_cpu(history)
    risk = predictor.assess_risk(history)

    print(f"- 실제 타깃 CPU (y_last): {y_last.item():.4f}")
    print(f"- 예측된 다음 CPU:       {pred_cpu:.4f}")

    if risk is None:
        print("- 위험도: history 길이가 부족해서 평가 불가")
    else:
        print("\n  위험도 평가 결과:")
        print(f"    status      : {risk['status']}")
        print(f"    risk_score  : {risk['risk_score']:.4f}")
        print(f"    current_cpu : {risk['current_cpu']:.4f}")
        print(f"    predicted_cpu: {risk['predicted_cpu']:.4f}")

    print("\n[완료] 데이터셋 → 학습 → 모델 로드 → 예측까지 전체 파이프라인 테스트 끝.")


if __name__ == "__main__":
    main()
