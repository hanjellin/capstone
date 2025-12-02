# UI/pages/monitor.py
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
)

from engine import collector, metrics_buffer


class HistoryGraph(QWidget):
    """
    간단한 실시간 라인 그래프 위젯.
    마지막 N개의 값을 저장하고, 0~max_value 범위에서 선으로 그린다.
    """

    def __init__(self, title: str, unit: str, max_value: float = 100.0,
                 color: QColor | None = None, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.max_value = float(max_value)
        self.values: list[float] = []
        self.max_points = 60  # 약 60초 정도의 히스토리

        self.color = color or QColor(46, 204, 113)  # 기본 초록색
        self.setMinimumHeight(70)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def add_value(self, v):
        if v is None:
            return
        try:
            v = float(v)
        except (TypeError, ValueError):
            return

        # 0 ~ max_value 범위로 클램프
        v = max(0.0, min(v, self.max_value))
        self.values.append(v)
        if len(self.values) > self.max_points:
            self.values.pop(0)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        full_rect = self.rect()
        # 그래프 영역 여백 조금 주기
        rect = full_rect.adjusted(8, 8, -8, -20)

        # 배경
        painter.fillRect(rect, Qt.white)

        # 테두리
        painter.setPen(QPen(Qt.lightGray, 1))
        painter.drawRect(rect)

        # 가로 그리드 (25, 50, 75%)
        for frac in (0.25, 0.5, 0.75):
            y = rect.bottom() - frac * rect.height()
            y_int = int(y)  # 🔧 float → int 캐스팅
            painter.setPen(QPen(Qt.lightGray, 1, Qt.DashLine))
            painter.drawLine(rect.left(), y_int, rect.right(), y_int)

        # 현재 값 텍스트
        painter.setPen(Qt.black)
        current = self.values[-1] if self.values else 0.0
        text = f"{self.title}: {current:.1f}{self.unit}"
        painter.drawText(rect.left(), rect.bottom() + 14, text)

        # 데이터가 2포인트 이상일 때만 선 그리기
        if len(self.values) < 2:
            return

        painter.setPen(QPen(self.color, 2))

        # x축은 고정된 max_points 기준으로 균등 분배
        n = len(self.values)
        for i in range(n - 1):
            x1 = rect.left() + (i / (self.max_points - 1)) * rect.width()
            x2 = rect.left() + ((i + 1) / (self.max_points - 1)) * rect.width()

            y1 = rect.bottom() - (self.values[i] / self.max_value) * rect.height()
            y2 = rect.bottom() - (self.values[i + 1] / self.max_value) * rect.height()

            painter.drawLine(int(x1), int(y1), int(x2), int(y2))


class MonitorPage(QWidget):
    """
    모니터링 탭:
      - CPU 사용률 (%)
      - GPU 사용률 (%)
      - RAM 사용률 (%)
      - CPU 온도 (℃)
      - GPU 온도 (℃)
    를 실시간 라인 그래프로 표시한다.
    """

    def __init__(self):
        super().__init__()
        self._init_ui()
        self._init_timer()

    def _init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("실시간 모니터링")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(title)

        # 상단: 사용률 3개
        layout.addWidget(QLabel("사용률 (%)"))
        self.graph_cpu = HistoryGraph("CPU 사용률", "%", 100.0, QColor(52, 152, 219))
        self.graph_gpu = HistoryGraph("GPU 사용률", "%", 100.0, QColor(231, 76, 60))
        self.graph_ram = HistoryGraph("RAM 사용률", "%", 100.0, QColor(46, 204, 113))

        layout.addWidget(self.graph_cpu)
        layout.addWidget(self.graph_gpu)
        layout.addWidget(self.graph_ram)

        # 하단: 온도 2개
        layout.addWidget(QLabel("온도 (℃)"))
        self.graph_cpu_temp = HistoryGraph("CPU 온도", "℃", 120.0, QColor(241, 196, 15))
        self.graph_gpu_temp = HistoryGraph("GPU 온도", "℃", 120.0, QColor(155, 89, 182))

        layout.addWidget(self.graph_cpu_temp)
        layout.addWidget(self.graph_gpu_temp)

        self.setLayout(layout)

    def _init_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_metrics)
        self.timer.start(1000)  # 1초마다 업데이트

    def _update_metrics(self):
        metrics = collector.get_current_metrics()
        metrics_buffer.add_sample(metrics)

        cpu_usage = metrics.get("cpu_usage") or 0.0
        ram_usage = metrics.get("ram_usage") or 0.0
        gpu_usage = metrics.get("gpu_usage") or 0.0

        cpu_temp = metrics.get("cpu_temp")
        gpu_temp = metrics.get("gpu_temp")

        self.graph_cpu.add_value(cpu_usage)
        self.graph_gpu.add_value(gpu_usage)
        self.graph_ram.add_value(ram_usage)
        self.graph_cpu_temp.add_value(cpu_temp)
        self.graph_gpu_temp.add_value(gpu_temp)
