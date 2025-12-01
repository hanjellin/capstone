from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit

from engine import metrics_buffer, analyzer


class AnomalyPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("스파이크 / 이상 탐지 & LSTM 부하 예측"))

        self.btn_analyze_cpu = QPushButton("최근 CPU 온도 스파이크 분석")
        self.btn_analyze_cpu.clicked.connect(self.analyze_cpu)
        layout.addWidget(self.btn_analyze_cpu)

        self.btn_lstm_risk = QPushButton("LSTM 부하 예측 / 위험도 평가")
        self.btn_lstm_risk.clicked.connect(self.check_lstm_risk)
        layout.addWidget(self.btn_lstm_risk)

        self.text_result = QTextEdit()
        self.text_result.setReadOnly(True)
        layout.addWidget(self.text_result)

        self.setLayout(layout)

    def analyze_cpu(self):
        series = metrics_buffer.get_series("cpu_temp")
        if not series:
            self.text_result.setPlainText(
                "CPU 온도 데이터가 충분하지 않습니다.\n"
                "모니터링 탭을 잠시 켜두었다가 다시 시도하세요."
            )
            return

        info = analyzer.detect_spikes(series)
        indices = info["indices"]
        om = info["original_mean"]
        cm = info["cleaned_mean"]

        lines = []
        lines.append("[스파이크 분석 결과]")
        lines.append(f"- 데이터 개수: {len(series)}")
        lines.append(f"- 원본 평균 온도: {om:.2f}℃")
        if cm is not None:
            lines.append(f"- 스파이크 제거 후 평균 온도: {cm:.2f}℃")
        lines.append(f"- 스파이크 감지 개수: {len(indices)}")

        if indices:
            preview = ", ".join(str(i) for i in indices[:10])
            lines.append(f"- 스파이크 인덱스(일부): {preview}")
        else:
            lines.append("- 특이한 급상승 패턴 없음")

        self.text_result.setPlainText("\n".join(lines))

    def check_lstm_risk(self):
        try:
            risk = analyzer.assess_load_risk()
        except Exception as e:
            self.text_result.setPlainText(
                f"[LSTM 부하 예측 오류]\n{e}\n"
                "internal/model_load_lstm.pth 와 torch 설치를 확인하세요."
            )
            return

        if risk is None:
            self.text_result.setPlainText(
                "[LSTM 부하 예측]\n"
                "히스토리가 충분하지 않아서 위험도를 계산할 수 없습니다.\n"
                "모니터링 탭을 일정 시간 켜두고 다시 시도해 주세요."
            )
            return

        status = risk["status"]
        score = risk["risk_score"]
        pred_cpu = risk["predicted_cpu"]
        cur_cpu = risk["current_cpu"]

        lines = []
        lines.append("[LSTM 부하 예측 결과]")
        lines.append(f"- 현재 CPU 사용률: {cur_cpu:.1f}%")
        lines.append(f"- 다음 시점 예측 CPU: {pred_cpu:.1f}%")
        lines.append(f"- 위험도 스코어 (0~1): {score:.3f}")
        lines.append(f"- 상태: {status}")

        if status == "NORMAL":
            lines.append("→ 단기적으로 큰 부하 증가는 예상되지 않습니다.")
        elif status == "WARN":
            lines.append("→ CPU 부하가 다소 올라갈 가능성이 있어 주의가 필요합니다.")
        else:
            lines.append("→ 곧 CPU 부하가 크게 증가할 것으로 예측됩니다. 불필요한 프로그램 종료를 권장합니다.")

        self.text_result.setPlainText("\n".join(lines))
