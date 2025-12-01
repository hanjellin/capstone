from PyQt5.QtWidgets import QMainWindow, QTabWidget

from engine import collector, report_manager

from ui.pages.dashboard import DashboardPage
from ui.pages.specs import SpecsPage
from ui.pages.monitor import MonitorPage
from ui.pages.anomaly import AnomalyPage
from ui.pages.report_page import ReportPage
from ui.pages.game_zone import GameZonePage
from ui.pages.upgrade_plan import UpgradePlanPage
from ui.pages.hud_page import HUDPage
from ui.pages.settings_page import SettingsPage
from ui.pages.tools_page import ToolsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DFY - Desktop For You")
        self.resize(1200, 800)

        self.report_manager = report_manager.ReportManager()
        self.specs = collector.get_system_specs()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.dashboard_page = DashboardPage(self.specs, self.report_manager)
        self.specs_page = SpecsPage(self.specs)
        self.monitor_page = MonitorPage()
        self.anomaly_page = AnomalyPage()
        self.report_page = ReportPage(self.report_manager)
        self.game_zone_page = GameZonePage(self.specs)
        self.upgrade_plan_page = UpgradePlanPage(self.specs)
        self.hud_page = HUDPage()
        self.settings_page = SettingsPage()
        self.tools_page = ToolsPage()

        self.tabs.addTab(self.dashboard_page, "Dashboard")
        self.tabs.addTab(self.specs_page, "사양")
        self.tabs.addTab(self.monitor_page, "모니터")
        self.tabs.addTab(self.anomaly_page, "스파이크/부하예측")
        self.tabs.addTab(self.report_page, "리포트")
        self.tabs.addTab(self.game_zone_page, "Game Zone")
        self.tabs.addTab(self.upgrade_plan_page, "스펙업 플랜")
        self.tabs.addTab(self.hud_page, "HUD 설정")
        self.tabs.addTab(self.tools_page, "Tools")
        self.tabs.addTab(self.settings_page, "설정")

        self.dashboard_page.diagnosis_finished.connect(self.report_page.reload_reports)
