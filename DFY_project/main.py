# main.py
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from UI.main_window import MainWindow  # ← 기존과 동일 경로 사용


def _preflight_autoencoder():
    """
    프로젝트 시작 전에 Autoencoder 모델/임계값이 없으면
    한 번 자동으로 학습시키는 프리플라이트.

    - internal/model_autoencoder.pth
    - internal/ae_thresholds.json
    둘 다 없으면 train_ae를 실행한다.
    실패해도 전체 프로그램이 죽지는 않고,
    AE 기능만 DISABLED 상태로 두도록 설계.
    """
    from model.train_ae import train_ae  # 늦게 import 해서 의존성 최소화

    model_path = Path("internal/model_autoencoder.pth")
    thresh_path = Path("internal/ae_thresholds.json")

    if model_path.exists() and thresh_path.exists():
        print("[DFY][AE] Autoencoder 모델 및 임계값 파일이 이미 존재합니다.")
        return

    print("[DFY][AE] Autoencoder 모델이 없습니다. 최초 1회 자동 학습을 시작합니다...")

    try:
        # 필요하다면 epoch 수(예: 5~10) 조절 가능
        train_ae(
            daily_dir="data/daily",
            seq_len=30,
            batch_size=64,
            num_epochs=5,   # 너무 오래 걸리면 여기 줄이면 됨
            lr=1e-3,
        )
        print("[DFY][AE] Autoencoder 학습이 완료되었습니다.")
    except Exception as e:
        # 학습 실패해도 UI는 띄우고, AE만 비활성화 상태로 둔다.
        print("[DFY][AE][WARN] Autoencoder 학습 중 오류가 발생했습니다:")
        print("  ", repr(e))
        print("[DFY][AE][WARN] AE 기반 이상 탐지 기능은 DISABLED 상태로 동작합니다.")


def main():
    # 1. Autoencoder 프리플라이트 (필요시 자동 학습)
    _preflight_autoencoder()

    # 2. 기존과 동일하게 UI 실행
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

