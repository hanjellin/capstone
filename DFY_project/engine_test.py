# test_engine_model.py
from __future__ import annotations

import traceback

def step(name, fn):
    print(f"\n=== STEP: {name} ===")
    try:
        result = fn()
        print(f"[OK] {name}")
        return result
    except Exception:
        print(f"[FAIL] {name}")
        traceback.print_exc()
        raise  # 여기서 바로 종료되게


def main():
    # 1. torch import 확인
    def _step_torch():
        import torch
        print(f"torch version: {torch.__version__}")
    step("import torch", _step_torch)

    # 2. dataset import + 간단한 객체 생성 (CSV까지는 안 읽게)
    def _step_dataset():
        from model import dataset
        print("FEATURE_KEYS:", dataset.FEATURE_KEYS)
    step("import model.dataset", _step_dataset)

    # 3. LSTM 모델 정의 import
    def _step_lstm():
        from model.lstm_model import LoadLSTM
        m = LoadLSTM()
        print("LSTM created:", type(m))
    step("import model.lstm_model + instantiate", _step_lstm)

    # 4. predictor import + 모델 로드 시도 (internal/model_load_lstm.pth)
    def _step_predictor():
        from model.predictor import LoadPredictor
        pred = LoadPredictor(
            model_path="internal/model_load_lstm.pth",
            seq_len=30,
        )
        print("Predictor created:", type(pred))
        return pred
    predictor = step("import model.predictor + LoadPredictor()", _step_predictor)

    # 5. engine.metrics_buffer / collector / analyzer import
    def _step_engine_imports():
        from engine import metrics_buffer, collector, analyzer
        print("metrics_buffer:", metrics_buffer.__name__)
        print("collector:", collector.__name__)
        print("analyzer:", analyzer.__name__)
        return metrics_buffer, collector, analyzer
    metrics_buffer, collector, analyzer = step("import engine.*", _step_engine_imports)

    # 6. collector로 한 번 값 읽고, metrics_buffer에 추가
    def _step_collect_and_buffer():
        metrics = collector.get_current_metrics()
        print("current metrics keys:", list(metrics.keys()))
        metrics_buffer.add_sample(metrics)
        hist = metrics_buffer.get_feature_history(limit=30)
        print(f"feature_history length: {len(hist)}")
        return hist
    history = step("collector + metrics_buffer", _step_collect_and_buffer)

    # 7. predictor로 예측 + analyzer 위험도 평가
    def _step_predict_and_risk():
        # predictor는 이미 위에서 만들었으니 그대로 사용
        pred_cpu = predictor.predict_next_cpu(history)
        risk = predictor.assess_risk(history)
        print("predicted next cpu:", pred_cpu)
        print("risk:", risk)
    step("predictor + analyzer.assess_load_risk (간접)", _step_predict_and_risk)

    print("\n=== ALL STEPS COMPLETED ===")


main()