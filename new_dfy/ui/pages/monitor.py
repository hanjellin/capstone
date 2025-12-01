from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar

from engine import collector, metrics_buffer


class MonitorPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._init_timer()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("실시간 모니터링"))

        self.cpu_bar = QProgressBar()
        self.cpu_bar.setFormat("CPU 사용률: %p%")
        self.ram_bar = QProgressBar()
        self.ram_bar.setFormat("RAM 사용률: %p%")
        self.disk_bar = QProgressBar()
        self.disk_bar.setFormat("디스크 사용률: %p%")

        layout.addWidget(self.cpu_bar)
        layout.addWidget(self.ram_bar)
        layout.addWidget(self.disk_bar)

        self.label_temps = QLabel("온도: -")
        layout.addWidget(self.label_temps)

        self.setLayout(layout)

    def _init_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_metrics)
        self.timer.start(1000)

    def _update_metrics(self):
        metrics = collector.get_current_metrics()
        metrics_buffer.add_sample(metrics)

        cpu_usage = metrics.get("cpu_usage") or 0
        ram_usage = metrics.get("ram_usage") or 0
        disk_usage = metrics.get("disk_usage") or 0

        self.cpu_bar.setValue(int(cpu_usage))
        self.ram_bar.setValue(int(ram_usage))
        self.disk_bar.setValue(int(disk_usage) if disk_usage is not None else 0)

        cpu_temp = metrics.get("cpu_temp")
        gpu_temp = metrics.get("gpu_temp")
        txt = "온도: "
        txt += f"CPU {cpu_temp:.1f}℃  " if cpu_temp is not None else "CPU -  "
        txt += f"GPU {gpu_temp:.1f}℃" if gpu_temp is not None else "GPU -"
        self.label_temps.setText(txt)
