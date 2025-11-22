import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use("TkAgg")
matplotlib.rc('font', family='Malgun Gothic')
matplotlib.rc('axes', unicode_minus=False)

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class PredictionPage(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.root = self.winfo_toplevel()

        # 제목
        self.label_title = ttk.Label(
            self,
            text="실시간 급상승 위험 탐지",
            font=("맑은 고딕", 16, "bold")
        )
        self.label_title.pack(pady=10)

        # 요약 메시지
        self.label_summary = ttk.Label(
            self,
            text="최근 60초 데이터를 분석하여 급상승 여부를 감지합니다.",
            font=("맑은 고딕", 12)
        )
        self.label_summary.pack(pady=5)

        # Matplotlib 그래프
        fig = Figure(figsize=(6, 4), dpi=100)
        self.ax = fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.get_tk_widget().pack()

        # 위험도 라벨
        self.label_risk = ttk.Label(self, text="", font=("맑은 고딕", 14))
        self.label_risk.pack(pady=10)

    # ---------------------------------------------------------
    # MonitoringPage에서 전달된 히스토리 데이터 기반 분석
    # ---------------------------------------------------------
    def update(self, monitoring):

        cpu_temp = monitoring.cpu_temp_history
        gpu_temp = monitoring.gpu_temp_history
        cpu_usage = monitoring.cpu_usage_history
        ram = monitoring.ram_history

        if len(cpu_temp) < 10:
            self.label_summary.config(text="데이터 수집 중... (10초 필요)")
            return

        # ---------------------------------------------------------
        # 1) 상승 속도 계산 (gradient)
        # ---------------------------------------------------------
        def gradient(values):
            if len(values) < 2:
                return 0
            return values[-1] - values[-10]  # 최근 10초 상승량

        cpu_temp_rise = gradient(cpu_temp)
        gpu_temp_rise = gradient(gpu_temp)
        cpu_usage_rise = gradient(cpu_usage)
        ram_rise = gradient(ram)

        # ---------------------------------------------------------
        # 2) 위험 판단 규칙
        # ---------------------------------------------------------
        risk_msg = []
        risk_level = 0   # 0=안전, 1=주의, 2=위험

        # CPU 온도 급상승
        if cpu_temp_rise > 8:
            risk_msg.append(f"🔴 CPU 온도 10초 상승량: +{cpu_temp_rise:.1f}°C (위험)")
            risk_level = max(risk_level, 2)
        elif cpu_temp_rise > 4:
            risk_msg.append(f"🟠 CPU 온도 상승량: +{cpu_temp_rise:.1f}°C (주의)")
            risk_level = max(risk_level, 1)

        # GPU 온도 급상승
        if gpu_temp_rise > 8:
            risk_msg.append(f"🔴 GPU 온도 10초 상승량: +{gpu_temp_rise:.1f}°C (위험)")
            risk_level = max(risk_level, 2)
        elif gpu_temp_rise > 4:
            risk_msg.append(f"🟠 GPU 온도 상승량: +{gpu_temp_rise:.1f}°C (주의)")
            risk_level = max(risk_level, 1)

        # CPU 사용률 급증
        if cpu_usage_rise > 50:
            risk_msg.append(f"🔴 CPU 사용률 10초 상승량: +{cpu_usage_rise:.1f}% (급증)")
            risk_level = max(risk_level, 2)
        elif cpu_usage_rise > 25:
            risk_msg.append(f"🟠 CPU 사용률 상승량: +{cpu_usage_rise:.1f}% (주의)")
            risk_level = max(risk_level, 1)

        # RAM 지속 증가
        if ram_rise > 20:
            risk_msg.append(f"🔴 RAM 10초 상승량: +{ram_rise:.1f}% (메모리 누수 의심)")
            risk_level = max(risk_level, 2)
        elif ram_rise > 10:
            risk_msg.append(f"🟠 RAM 상승량: +{ram_rise:.1f}% (주의)")
            risk_level = max(risk_level, 1)

        # ---------------------------------------------------------
        # 3) 위험도 라벨 표시
        # ---------------------------------------------------------
        colors = ["green", "orange", "red"]
        texts = ["양호", "주의", "위험"]

        self.label_risk.config(
            text=f"상태: {texts[risk_level]}",
            foreground=colors[risk_level]
        )

        # ---------------------------------------------------------
        # 4) 요약 메시지 출력
        # ---------------------------------------------------------
        if risk_msg:
            summary = "\n".join(risk_msg)
        else:
            summary = "🟢 현재 급상승 징후 없음 (안정적)"

        self.label_summary.config(text=summary)

        # ---------------------------------------------------------
        # 5) 그래프 그리기
        # ---------------------------------------------------------
        self.ax.clear()
        self.ax.plot(cpu_temp, label="CPU 온도", color="red")
        self.ax.plot(gpu_temp, label="GPU 온도", color="orange")
        self.ax.plot(cpu_usage, label="CPU 사용률", color="lime")
        self.ax.plot(ram, label="RAM 사용률", color="cyan")

        self.ax.set_title("최근 60초 상태 변화")
        self.ax.legend(loc="upper left")

        self.canvas.draw()
