from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QHBoxLayout

from engine import collector, analyzer, metrics_buffer


class DashboardPage(QWidget):
    diagnosis_finished = pyqtSignal()

    def __init__(self, specs: dict, report_manager):
        super().__init__()
        self.specs = specs
        self.report_manager = report_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        self.label_score = QLabel("전체 점수: -")
        self.label_status = QLabel("상태: -")
        self.label_score.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.label_status.setStyleSheet("font-size: 18px;")

        layout.addWidget(self.label_score)
        layout.addWidget(self.label_status)

        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("AI 원클릭 진단 실행")
        self.btn_run.clicked.connect(self.run_diagnosis)
        btn_layout.addWidget(self.btn_run)
        layout.addLayout(btn_layout)

        self.text_summary = QTextEdit()
        self.text_summary.setReadOnly(True)
        layout.addWidget(QLabel("진단 결과 요약"))
        layout.addWidget(self.text_summary)

        self.setLayout(layout)

    def run_diagnosis(self):
        self.btn_run.setEnabled(False)
        self.btn_run.setText("진단 중...")

        metrics = collector.get_current_metrics()
        history_cpu = metrics_buffer.get_series("cpu_temp")

        report = analyzer.run_full_diagnosis(self.specs, metrics, history_cpu)
        self.report_manager.append_report(report)

        self.label_score.setText(f"전체 점수: {report['score']}점")
        self.label_status.setText(f"상태: {report['status']}")
        text = report["summary"] + "\n\n" + "\n".join(f"- {i}" for i in report["issues"])
        self.text_summary.setPlainText(text)

        self.btn_run.setEnabled(True)
        self.btn_run.setText("AI 원클릭 진단 실행")

        self.diagnosis_finished.emit()
