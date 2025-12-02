from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QTextEdit, QFormLayout
from engine import game_recommender


class GameZonePage(QWidget):
    def __init__(self, specs: dict):
        super().__init__()
        self.specs = specs
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Game Zone - 내 사양으로 게임 성능 가늠하기"))

        form = QFormLayout()

        self.combo_game = QComboBox()
        self.combo_game.addItems([
            "League of Legends",
            "Valorant",
            "Overwatch 2",
            "PUBG: Battlegrounds",
            "AAA High-End",
        ])

        self.combo_res = QComboBox()
        self.combo_res.addItems(["1920x1080", "2560x1440", "3840x2160"])

        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["Low", "Medium", "High", "Ultra"])

        form.addRow("게임 선택", self.combo_game)
        form.addRow("해상도", self.combo_res)
        form.addRow("그래픽 옵션", self.combo_quality)
        layout.addLayout(form)

        self.btn_calc = QPushButton("예상 성능 계산")
        self.btn_calc.clicked.connect(self.calc)
        layout.addWidget(self.btn_calc)

        self.text_result = QTextEdit()
        self.text_result.setReadOnly(True)
        layout.addWidget(self.text_result)

        self.setLayout(layout)

    def calc(self):
        game = self.combo_game.currentText()
        res = self.combo_res.currentText()
        quality = self.combo_quality.currentText()

        result = game_recommender.recommend(game, self.specs, res, quality)

        text = []
        text.append(result["summary"])
        text.append("")
        text.append(f"내부 퍼포먼스 인덱스: {result['perf_index']:.2f}")
        self.text_result.setPlainText("\n".join(text))
