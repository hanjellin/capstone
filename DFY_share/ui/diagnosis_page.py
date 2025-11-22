import tkinter as tk
from tkinter import ttk
import joblib
import pandas as pd
import os

import sklearn              # PyInstaller가 sklearn 패키지를 포함하도록
import sklearn.ensemble._forest  # ⭐ RandomForest가 쓰는 내부 모듈까지 강제 import

from utils.resources import resource_path


class DiagnosisPage(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        # 제목
        self.label_title = ttk.Label(self, text="AI 즉시 진단 결과", font=("맑은 고딕", 16, "bold"))
        self.label_title.pack(pady=10)

        # 위험도 표시
        self.progress = ttk.Progressbar(self, length=400, maximum=2)
        self.progress.pack(pady=10)

        self.label_risk = ttk.Label(self, text="위험도: -", font=("맑은 고딕", 14))
        self.label_risk.pack()

        # 상세 정보
        self.details = tk.Text(self, height=14, width=90, font=("Consolas", 10))
        self.details.pack(pady=10)

        # 모델 로드 (개발/exe 둘 다 동작하도록 resource_path 사용)
        model_path = resource_path(os.path.join("model", "snapshot_model.pkl"))
        self.model = joblib.load(model_path)

        # 마지막 진단 결과 저장용 (AI 케어 탭에서 사용)
        self.last_result = None

    def update(self, info):
        # collect_specs() 구조에 맞춰 안전하게 매핑

        cpu_usage = info["cpu"].get("usage_percent", 0)
        cpu_temp = info["cpu"].get("temperature", 45)

        gpu_temp = info["gpu"].get("temperature", 40)
        gpu_usage = 0
        gpu_mem = 0

        disk_info = info["disk"][0] if info["disk"] else {}
        disk_temp = disk_info.get("temperature", 30)
        disk_life = disk_info.get("life", 100)
        disk_spare = disk_info.get("spare", 100)

        cols = [
            "cpu_usage", "cpu_temp",
            "gpu_temp", "gpu_usage", "gpu_mem",
            "disk_temp", "disk_life", "disk_spare"
        ]

        X = pd.DataFrame([[
            cpu_usage, cpu_temp,
            gpu_temp, gpu_usage, gpu_mem,
            disk_temp, disk_life, disk_spare
        ]], columns=cols)

        pred = int(self.model.predict(X)[0])  # 0~2

        self.progress["value"] = pred
        risk_text = ["양호", "주의", "위험"][pred]
        colors = ["green", "orange", "red"]
        self.label_risk.config(text=f"위험도: {pred} — {risk_text}", foreground=colors[pred])

        out = ""
        out += f"CPU 사용량:   {cpu_usage:.1f}%\n"
        out += f"CPU 온도:     {cpu_temp:.1f}°C\n"
        out += f"GPU 온도:     {gpu_temp:.1f}°C\n"
        out += f"디스크 사용률: {disk_info.get('percent', 'N/A')}%\n"
        out += f"디스크 온도(가정): {disk_temp:.1f}°C\n"

        if pred == 0:
            out += "\n🟢 시스템 상태는 전반적으로 양호합니다."
        elif pred == 1:
            out += "\n🟠 일부 지표에서 경고 수준이 감지되었습니다. AI 케어 탭에서 개선 방법을 참고하세요."
        else:
            out += "\n🔴 여러 지표에서 위험 수준이 감지되었습니다. 즉시 조치가 필요합니다."

        self.details.delete("1.0", tk.END)
        self.details.insert(tk.END, out)

        # CarePage 등에서 활용할 수 있도록 마지막 결과 저장
        self.last_result = {
            "risk_class": pred,
            "cpu_usage": cpu_usage,
            "cpu_temp": cpu_temp,
            "gpu_temp": gpu_temp,
            "disk_usage": disk_info.get("percent", 0),
        }
