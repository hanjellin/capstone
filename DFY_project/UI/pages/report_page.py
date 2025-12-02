from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QTextEdit, QSplitter
from PyQt5.QtCore import Qt


class ReportPage(QWidget):
    def __init__(self, report_manager):
        super().__init__()
        self.report_manager = report_manager
        self._init_ui()
        self.reload_reports()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("진단 리포트"))

        splitter = QSplitter(Qt.Vertical)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["시간", "점수", "상태", "요약"])
        self.table.currentCellChanged.connect(self._on_selection_changed)

        self.text_detail = QTextEdit()
        self.text_detail.setReadOnly(True)

        splitter.addWidget(self.table)
        splitter.addWidget(self.text_detail)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)
        self.setLayout(layout)

    def reload_reports(self):
        reports = self.report_manager.load_reports()
        self._reports = reports

        self.table.setRowCount(len(reports))
        for row, r in enumerate(reports):
            self.table.setItem(row, 0, QTableWidgetItem(r.get("timestamp", "")))
            self.table.setItem(row, 1, QTableWidgetItem(str(r.get("score", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(r.get("status", "")))
            self.table.setItem(row, 3, QTableWidgetItem(r.get("summary", "")))
        self.table.resizeColumnsToContents()

        if reports:
            self.table.setCurrentCell(len(reports) - 1, 0)

    def _on_selection_changed(self, currentRow, *_):
        if currentRow < 0 or currentRow >= len(self._reports):
            self.text_detail.clear()
            return

        r = self._reports[currentRow]
        lines = []
        lines.append(f"[시간] {r.get('timestamp', '')}")
        lines.append(f"[점수] {r.get('score', '')}점 ({r.get('status', '')})")
        lines.append("")
        lines.append("[요약]")
        lines.append(r.get("summary", ""))
        lines.append("")
        lines.append("[상세 이슈]")
        for issue in r.get("issues", []):
            lines.append(f"- {issue}")

        spike_info = r.get("spike_info")
        if spike_info:
            lines.append("")
            lines.append("[스파이크 분석]")
            lines.append(f"- 감지 개수: {len(spike_info.get('indices', []))}")
            om = spike_info.get("original_mean")
            cm = spike_info.get("cleaned_mean")
            if om is not None:
                lines.append(f"- 원본 평균: {om:.2f}℃")
            if cm is not None:
                lines.append(f"- 정제 후 평균: {cm:.2f}℃")

        load_risk = r.get("load_risk")
        if load_risk:
            lines.append("")
            lines.append("[LSTM 부하 예측 요약]")
            lines.append(f"- 상태: {load_risk.get('status')}")
            lines.append(f"- 위험도: {load_risk.get('risk_score', 0.0):.3f}")
            pc = load_risk.get("predicted_cpu")
            cc = load_risk.get("current_cpu")
            if cc is not None:
                lines.append(f"- 당시 CPU: {cc:.1f}%")
            if pc is not None:
                lines.append(f"- 예측 CPU: {pc:.1f}%")

        self.text_detail.setPlainText("\n".join(lines))
