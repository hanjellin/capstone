from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem


class SpecsPage(QWidget):
    def __init__(self, specs: dict):
        super().__init__()
        self.specs = specs
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("시스템 사양 정보"))

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["항목", "값"])
        layout.addWidget(self.table)

        self._populate_table()
        self.setLayout(layout)

    def _add_row(self, row, key, value):
        self.table.setItem(row, 0, QTableWidgetItem(key))
        self.table.setItem(row, 1, QTableWidgetItem(str(value)))

    def _populate_table(self):
        rows = []

        os_info = self.specs.get("os", {})
        rows.append(("OS", f"{os_info.get('system', '')} {os_info.get('release', '')}"))
        rows.append(("OS 버전", os_info.get("version", "")))
        rows.append(("호스트 이름", os_info.get("node", "")))

        cpu = self.specs.get("cpu", {})
        rows.append(("CPU 모델", cpu.get("name", "")))
        rows.append(("물리 코어 수", cpu.get("physical_cores", "")))
        rows.append(("논리 코어 수", cpu.get("logical_cores", "")))
        base_freq = cpu.get("base_freq_mhz")
        rows.append(("CPU 기본 클럭(MHz)", f"{base_freq:.0f}" if base_freq else "-"))

        ram = self.specs.get("ram", {})
        rows.append(("RAM 총 용량(GB)", f"{ram.get('total_gb', 0):.1f}"))

        gpus = self.specs.get("gpus", [])
        if not gpus:
            rows.append(("GPU", "GPU 정보 없음"))
        else:
            for idx, gpu in enumerate(gpus, start=1):
                rows.append((f"GPU{idx} 이름", gpu.get("name", "")))
                rows.append((f"GPU{idx} VRAM(MB)", gpu.get("memory_total_mb", "")))

        disks = self.specs.get("disks", [])
        for idx, d in enumerate(disks, start=1):
            label = f"디스크{idx} ({d.get('device', '')})"
            size = f"{d.get('total_gb', 0):.1f} GB"
            rows.append((label, f"{size}, 사용률 {d.get('percent', 0):.1f}%"))

        self.table.setRowCount(len(rows))
        for i, (k, v) in enumerate(rows):
            self._add_row(i, k, v)
        self.table.resizeColumnsToContents()
