from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QComboBox, QFormLayout


class HUDPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("HUD 설정 (오버레이에 표시할 정보 선택)"))

        self.chk_fps = QCheckBox("FPS 표시")
        self.chk_cpu = QCheckBox("CPU 사용률/온도 표시")
        self.chk_gpu = QCheckBox("GPU 사용률/온도 표시")
        self.chk_ram = QCheckBox("RAM 사용률 표시")

        layout.addWidget(self.chk_fps)
        layout.addWidget(self.chk_cpu)
        layout.addWidget(self.chk_gpu)
        layout.addWidget(self.chk_ram)

        form = QFormLayout()
        self.combo_position = QComboBox()
        self.combo_position.addItems(["좌상단", "우상단", "좌하단", "우하단"])
        form.addRow("표시 위치", self.combo_position)

        self.combo_font = QComboBox()
        self.combo_font.addItems(["작게", "보통", "크게"])
        form.addRow("글자 크기", self.combo_font)

        layout.addLayout(form)

        info = QLabel("※ 현재는 HUD 설정 UI만 제공하며, 실제 인게임 오버레이는 별도 모듈로 연동할 수 있습니다.")
        layout.addWidget(info)

        self.setLayout(layout)
