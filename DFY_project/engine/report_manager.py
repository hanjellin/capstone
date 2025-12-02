import json
import os


class ReportManager:
    def __init__(self, path: str | None = None):
        if path is None:
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
            os.makedirs(base_dir, exist_ok=True)
            path = os.path.join(base_dir, "reports.json")
        self.path = os.path.normpath(path)

    def load_reports(self):
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def save_reports(self, reports):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(reports, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Failed to save reports:", e)

    def append_report(self, report: dict):
        reports = self.load_reports()
        reports.append(report)
        self.save_reports(reports)
