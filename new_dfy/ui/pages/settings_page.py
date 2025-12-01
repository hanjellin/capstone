from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QFormLayout, QLineEdit


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("설정"))

        form = QFormLayout()

        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["라이트", "다크"])
        form.addRow("테마", self.combo_theme)

        self.line_data_path = QLineEdit()
        self.line_data_path.setPlaceholderText("데이터/리포트 저장 경로 (기본값 사용 시 비워두세요)")
        form.addRow("데이터 경로", self.line_data_path)

        self.combo_auto_diag = QComboBox()
        self.combo_auto_diag.addItems(["사용 안 함", "실행 시 간단 진단"])
        form.addRow("자동 진단", self.combo_auto_diag)

        layout.addLayout(form)

        info = QLabel("※ 이 값들은 현재 UI 상에서만 관리되며, 필요 시 설정 파일/테마 로직을 추가할 수 있습니다.")
        layout.addWidget(info)

        self.setLayout(layout)
