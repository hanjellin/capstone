import os
import psutil
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton


class ToolsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("간단 Tools / 유틸리티"))

        self.btn_show_disk = QPushButton("시스템 디스크 사용량 보기")
        self.btn_show_disk.clicked.connect(self.show_disk)
        layout.addWidget(self.btn_show_disk)

        self.btn_top_procs = QPushButton("상위 CPU 사용 프로세스 5개 보기")
        self.btn_top_procs.clicked.connect(self.show_top_procs)
        layout.addWidget(self.btn_top_procs)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

        info = QLabel("※ 안전을 위해 실제 삭제/종료 기능은 제공하지 않고, 정보 확인 위주로 구성했습니다.")
        layout.addWidget(info)

        self.setLayout(layout)

    def show_disk(self):
        try:
            system_drive = os.getenv("SystemDrive", "C:") + "\\"
            usage = psutil.disk_usage(system_drive)
            text = []
            text.append(f"드라이브: {system_drive}")
            text.append(f"총 용량: {usage.total / (1024 ** 3):.1f} GB")
            text.append(f"사용 중: {usage.used / (1024 ** 3):.1f} GB")
            text.append(f"여유 공간: {usage.free / (1024 ** 3):.1f} GB")
            text.append(f"사용률: {usage.percent:.1f}%")
            self.text.setPlainText("\n".join(text))
        except Exception as e:
            self.text.setPlainText(f"디스크 정보를 가져오는 중 오류 발생: {e}")

    def show_top_procs(self):
        procs = []
        for p in psutil.process_iter(attrs=["pid", "name", "cpu_percent"]):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
        top = procs[:5]

        lines = ["상위 CPU 사용 프로세스 5개:"]
        for p in top:
            lines.append(f"- PID {p['pid']} / {p['name']} / CPU {p['cpu_percent']:.1f}%")

        self.text.setPlainText("\n".join(lines))
