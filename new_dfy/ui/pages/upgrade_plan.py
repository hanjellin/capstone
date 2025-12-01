from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from engine import upgrade_planner


class UpgradePlanPage(QWidget):
    def __init__(self, specs: dict):
        super().__init__()
        self.specs = specs
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("단계별 스펙업 플랜"))

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

        self.setLayout(layout)
        self.refresh_plan()

    def refresh_plan(self):
        plan = upgrade_planner.generate_plan(self.specs)
        self.text.setPlainText(plan)
