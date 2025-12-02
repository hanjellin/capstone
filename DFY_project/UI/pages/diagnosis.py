from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
)
from PyQt5.QtCore import Qt


class DiagnosisDialog(QDialog):
    """
    DFY 원클릭 진단 결과 팝업
    - snapshot(summary) + risk + top_process 리스트를 받아
      간단한 한국어 리포트를 만들어 보여준다.
    """

    def __init__(self, snapshot: dict, risk: dict, top_procs: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DFY - AI 원클릭 진단 결과")
        self.resize(500, 420)
        self.snapshot = snapshot
        self.risk = risk
        self.top_procs = top_procs or []

        self._init_ui()
        self._build_report_text()

    def _init_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)
        self.setLayout(root)

        title = QLabel("🧠 DFY AI 원클릭 진단")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root.addWidget(scroll, 1)

        inner = QWidget()
        self.inner_layout = QVBoxLayout()
        self.inner_layout.setAlignment(Qt.AlignTop)
        inner.setLayout(self.inner_layout)
        scroll.setWidget(inner)

        self.report_label = QLabel("")
        self.report_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.report_label.setWordWrap(True)
        self.report_label.setStyleSheet("font-size: 13px;")
        self.inner_layout.addWidget(self.report_label)

        # 닫기 버튼
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet("padding: 6px 14px;")
        root.addWidget(btn_close, alignment=Qt.AlignRight)

    def _build_report_text(self):
        snap = self.snapshot or {}
        risk = self.risk or {}

        cpu = float(snap.get("cpu", 0.0))
        ram = float(snap.get("ram", 0.0))
        gpu_val = snap.get("gpu", 0.0)
        gpu = 0.0 if gpu_val is None else float(gpu_val)
        gpu_temp_val = snap.get("gpu_temp", 0.0)
        gpu_temp = 0.0 if gpu_temp_val is None else float(gpu_temp_val)
        disk_r = float(snap.get("disk_read", 0.0))
        disk_w = float(snap.get("disk_write", 0.0))
        net_up = float(snap.get("net_upload", 0.0))
        net_down = float(snap.get("net_download", 0.0))

        status = risk.get("status", "UNKNOWN")
        risk_score = float(risk.get("risk_score", 0.0)) * 100.0
        pred_cpu = risk.get("predicted_cpu", None)
        cur_cpu = float(risk.get("current_cpu", cpu))

        # 1. 전체 상태 요약
        top_lines = []

        if status == "NORMAL":
            top_lines.append("현재 시스템 상태는 안정적인 편입니다.")
            if risk_score < 30:
                top_lines.append("전반적인 자원 사용률이 낮고, AI가 판단한 위험도도 낮은 수준입니다.")
            else:
                top_lines.append("일부 순간적인 부하는 있지만, 전체적으로 위험한 수준은 아닙니다.")
        elif status == "WARN":
            top_lines.append("현재 시스템 상태는 주의가 필요한 수준입니다.")
            top_lines.append("CPU/RAM 또는 GPU 사용률이 꽤 높은 구간이 있고, 일정 시간 유지되는 경향이 있습니다.")
        elif status == "CRITICAL":
            top_lines.append("현재 시스템 상태는 위험 수준(CRITICAL) 입니다.")
            top_lines.append("지속적인 과부하가 감지되었고, 현재 작업 또는 게임에서 렉/프레임 드랍이 발생할 가능성이 높습니다.")
        else:
            top_lines.append("현재 시스템 상태를 명확히 판단하지 못했습니다.")
            top_lines.append("측정 데이터가 충분하지 않거나, 모델이 예상치 못한 패턴을 감지했습니다.")

        # 2. 수치 요약
        metric_lines = [
            "",
            "📊 주요 자원 사용률 스냅샷",
            f"  - CPU 현재: {cur_cpu:.1f}%"
            + (f" / 예측: {float(pred_cpu):.1f}%" if pred_cpu is not None else ""),
            f"  - RAM 현재: {ram:.1f}%",
            f"  - GPU 현재: {gpu:.1f}% / 온도: {gpu_temp:.0f}°C",
            f"  - 디스크: 읽기 {disk_r:.2f} MB/s / 쓰기 {disk_w:.2f} MB/s",
            f"  - 네트워크: 업 {net_up:.3f} Mbps / 다운 {net_down:.3f} Mbps",
            f"  - AI 위험도 점수: {risk_score:.1f}%",
        ]

        # 3. 위험 요소 분석
        risk_detail = ["", "⚠️ 위험 요소 분석"]
        has_issue = False

        if cur_cpu > 85 or (pred_cpu is not None and float(pred_cpu) > 90):
            risk_detail.append(
                "- CPU 사용률이 매우 높거나 곧 90% 이상으로 치솟을 것으로 예측됩니다."
            )
            has_issue = True

        if ram > 85:
            risk_detail.append("- RAM 사용률이 85% 이상으로, 메모리 부족으로 인한 버벅임 가능성이 있습니다.")
            has_issue = True

        if gpu > 90:
            risk_detail.append("- GPU 사용률이 90% 이상으로, 그래픽 작업/게임에서 프레임 드랍이 발생할 수 있습니다.")
            has_issue = True

        if gpu_temp > 80:
            risk_detail.append("- GPU 온도가 80°C 이상으로, 장시간 사용 시 발열 관리가 필요합니다.")
            has_issue = True

        if not has_issue:
            risk_detail.append("- 뚜렷한 과부하나 위험 요소는 감지되지 않았습니다.")

        # 4. 상위 프로세스
        proc_lines = ["", "🧾 상위 프로세스 (메모리 기준 Top 5)"]
        if not self.top_procs:
            proc_lines.append("  - 프로세스 정보를 가져오지 못했습니다.")
        else:
            for p in self.top_procs:
                name = p.get("name", "unknown")
                pid = p.get("pid", 0)
                cpu_p = float(p.get("cpu_percent", 0.0))
                mem_p = float(p.get("memory_percent", 0.0))
                proc_lines.append(
                    f"  - {name} (PID {pid}) : CPU {cpu_p:.1f}% / MEM {mem_p:.1f}%"
                )

        # 5. 권장 조치
        suggestion = ["", "🛠 권장 조치"]
        if status == "CRITICAL" or has_issue:
            suggestion.append("- 사용하지 않는 프로그램이나 브라우저 탭을 우선적으로 종료해 주세요.")
            suggestion.append("- 필요하다면 게임/그래픽 옵션을 한 단계 낮추는 것을 권장합니다.")
            suggestion.append("- 발열이 심한 경우, 쿨링 패드나 먼지 청소 등 냉각 환경 개선을 고려해 주세요.")
        elif status == "WARN":
            suggestion.append("- 장시간 고부하 작업을 계속하면 과열 또는 성능 저하가 발생할 수 있습니다.")
            suggestion.append("- 중요 작업/게임을 진행 중이라면, 백그라운드 프로그램을 한 번 정리해 주세요.")
        else:
            suggestion.append("- 현재로서는 별도의 조치가 필요하지 않습니다.")
            suggestion.append("- 다만, 장시간 사용 시 주기적으로 DFY 진단을 실행해 상태를 확인해 주세요.")

        all_lines = top_lines + metric_lines + risk_detail + proc_lines + suggestion
        text = "\n".join(all_lines)
        self.report_label.setText(text)
