import tkinter as tk
from tkinter import ttk

from ui.styles import setup_styles
from ui.overview_page import OverviewPage
from ui.monitoring_page import MonitoringPage
from ui.raw_page import RawPage
from ui.diagnosis_page import DiagnosisPage
from ui.prediction_page import PredictionPage
from ui.care_page import CarePage

from data.loader import collect_specs


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("DFY - AI PC HealthCare System")
        self.root.geometry("1080x760")
        self.root.resizable(False, False)

        setup_styles(self.root)

        # 상단 메뉴 버튼
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=12, pady=(12, 8))

        ttk.Button(top, text="새로고침", command=self.refresh).pack(side="left")
        ttk.Button(top, text="AI 진단", command=self.run_diagnosis).pack(side="left", padx=8)
        ttk.Button(top, text="RAW 복사", command=self.copy_raw).pack(side="left", padx=8)

        # Notebook Tabs
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # 각 페이지 생성
        self.page_overview = OverviewPage(self.nb)
        self.page_monitor = MonitoringPage(self.nb)
        self.page_raw = RawPage(self.nb)
        self.page_diag = DiagnosisPage(self.nb)
        self.page_pred = PredictionPage(self.nb)
        self.page_care = CarePage(self.nb)

        # 탭 추가
        self.nb.add(self.page_overview, text="개요")
        self.nb.add(self.page_monitor, text="실시간 모니터링")
        self.nb.add(self.page_raw, text="RAW")
        self.nb.add(self.page_diag, text="AI 진단")
        self.nb.add(self.page_pred, text="예측")
        self.nb.add(self.page_care, text="AI 케어")

        self.refresh()

    # ---------------------------------------------------
    # 상단 버튼 액션
    # ---------------------------------------------------
    def refresh(self):
        info = collect_specs()
        self.page_overview.update(info)
        self.page_raw.update_json(info)

    def run_diagnosis(self):
        info = collect_specs()
        self.page_diag.update(info)

    def copy_raw(self):
        raw = self.page_raw.get_raw()
        self.root.clipboard_clear()
        self.root.clipboard_append(raw)

    # ---------------------------------------------------
    # 탭 전환 시 동작
    # ---------------------------------------------------
    def on_tab_change(self, event):
        tab_text = event.widget.tab(event.widget.index("current"))["text"]

        # 예측 탭 → 모니터링 페이지의 60초 히스토리를 기반으로 급상승 탐지
        if tab_text == "예측":
            self.page_pred.update(self.page_monitor)

        # AI 케어 탭 → 실시간 히스토리 + 마지막 AI 진단 결과를 함께 사용
        elif tab_text == "AI 케어":
            diag_result = getattr(self.page_diag, "last_result", None)
            self.page_care.update(self.page_monitor, diag_result)
