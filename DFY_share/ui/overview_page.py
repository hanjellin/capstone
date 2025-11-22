# ui/overview_page.py
import tkinter as tk
from tkinter import ttk

# 한국어 라벨 매핑 테이블
KOR_LABEL = {
    # OS
    "name": "이름",
    "version": "버전",
    "release": "릴리즈",
    "machine": "아키텍처",

    # CPU
    "model": "모델",
    "cores_physical": "물리 코어",
    "cores_logical": "논리 코어",
    "usage_percent": "사용률",

    # RAM
    "total_gb": "총 용량(GB)",
    "used_gb": "사용 중(GB)",
    "percent": "사용률",

    # GPU
    "vram_total_gb": "VRAM 총량(GB)",
    "vram_used_gb": "VRAM 사용량(GB)",
    "temperature": "온도(°C)",

    # DISK
    "device": "드라이브",
    "total_gb": "총 용량",
    "used_gb": "사용 용량",
    "percent": "사용률",
}

class OverviewPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.os_frame   = self._create_card("운영체제 (OS)")
        self.cpu_frame  = self._create_card("CPU")
        self.ram_frame  = self._create_card("RAM")
        self.gpu_frame  = self._create_card("GPU")
        self.disk_frame = self._create_card("디스크")

        self.os_frame.grid(   row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.cpu_frame.grid(  row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.ram_frame.grid(  row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.gpu_frame.grid(  row=1, column=1, sticky="nsew", padx=10, pady=10)
        self.disk_frame.grid( row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

    def _create_card(self, title):
        frame = ttk.Labelframe(self, text=title, style="Card.TLabelframe")

        inner = ttk.Frame(frame)
        inner.pack(fill="x", padx=10, pady=10)
        frame.inner = inner
        return frame

    # --------------------------------------
    # 딕셔너리를 한국어 라벨로 출력
    # --------------------------------------
    def _fill_kv(self, parent, data: dict):
        for widget in parent.winfo_children():
            widget.destroy()

        if not isinstance(data, dict):
            ttk.Label(parent, text=str(data)).pack(anchor="w")
            return

        for key, value in data.items():
            label = KOR_LABEL.get(key, key)  # 한국어 라벨 적용
            ttk.Label(parent, text=f"{label}: {value}", style="Val.TLabel").pack(anchor="w", pady=1)

    # --------------------------------------
    # 디스크는 리스트로 별도 처리
    # --------------------------------------
    def _fill_disk_list(self, parent, data: list):
        for widget in parent.winfo_children():
            widget.destroy()

        if not data:
            ttk.Label(parent, text="디스크 정보를 가져올 수 없음").pack(anchor="w")
            return

        for disk in data:
            name = disk["device"].replace("\\", "")  # 보기 좋게 정리
            line = f"{name}: {disk['used_gb']}GB / {disk['total_gb']}GB ({disk['percent']}%)"
            ttk.Label(parent, text=line).pack(anchor="w", pady=1)

    # --------------------------------------
    # 메인 업데이트 함수
    # --------------------------------------
    def update(self, info: dict):
        self._fill_kv(self.os_frame.inner, info.get("os", {}))
        self._fill_kv(self.cpu_frame.inner, info.get("cpu", {}))
        self._fill_kv(self.ram_frame.inner, info.get("ram", {}))
        self._fill_kv(self.gpu_frame.inner, info.get("gpu", {}))
        self._fill_disk_list(self.disk_frame.inner, info.get("disk", []))
