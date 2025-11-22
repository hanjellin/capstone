from tkinter import ttk
import json

class RawPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.text = ttk.Label(self, text="RAW JSON 출력 (준비중)")
        self.text.pack(pady=20)

    def update_json(self, info: dict):
        self.text.config(text=json.dumps(info, indent=2, ensure_ascii=False))

    def get_raw(self):
        return self.text.cget("text")
