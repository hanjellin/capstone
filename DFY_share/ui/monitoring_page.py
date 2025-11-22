import tkinter as tk
from tkinter import ttk
import psutil
import time


class MonitoringPage(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.root = self.winfo_toplevel()

        # -----------------------------
        # 시계열 데이터 버퍼 (최근 60초)
        # -----------------------------
        self.cpu_usage_history = []
        self.cpu_temp_history = []
        self.gpu_temp_history = []
        self.ram_history = []

        # -----------------------------
        # CPU 사용 그래프
        # -----------------------------
        self.cpu_canvas = tk.Canvas(self, width=600, height=200, bg="black")
        self.cpu_canvas.pack(pady=10)

        # -----------------------------
        # GPU 온도 그래프
        # -----------------------------
        self.gpu_canvas = tk.Canvas(self, width=600, height=200, bg="black")
        self.gpu_canvas.pack(pady=10)

        # -----------------------------
        # RAM 사용률 바
        # -----------------------------
        self.ram_bar = ttk.Progressbar(self, length=600, maximum=100)
        self.ram_bar.pack(pady=10)

        # -----------------------------
        # GPU 온도 표시 라벨
        # -----------------------------
        self.label_gpu_temp = ttk.Label(self, text="GPU 온도: -")
        self.label_gpu_temp.pack(pady=5)

        # GPU 온도 캐시 (너무 자주 센서 안 읽게)
        self._gpu_temp_cached = 40.0
        self._last_gpu_read_time = 0.0

        # -----------------------------
        # 업데이트 루프 시작
        # -----------------------------
        self.after(1000, self.update_loop)

    # =====================================================================
    # 60초 동안 히스토리 기록 & 그래프 업데이트
    # =====================================================================
    def update_loop(self):

        # --- CPU 사용률 ---
        cpu_usage = psutil.cpu_percent()
        self.cpu_usage_history.append(cpu_usage)
        self.cpu_usage_history = self.cpu_usage_history[-60:]  # 60초 유지

        # --- CPU 온도 ---
        cpu_temp = self.get_cpu_temp()
        self.cpu_temp_history.append(cpu_temp)
        self.cpu_temp_history = self.cpu_temp_history[-60:]

        # --- GPU 온도 (psutil만 사용, 콘솔 프로그램 X) ---
        gpu_temp = self.get_gpu_temp()
        self.gpu_temp_history.append(gpu_temp)
        self.gpu_temp_history = self.gpu_temp_history[-60:]

        # --- RAM ---
        ram = psutil.virtual_memory().percent
        self.ram_history.append(ram)
        self.ram_history = self.ram_history[-60:]
        self.ram_bar["value"] = ram

        # --- GPU temp label ---
        self.label_gpu_temp.config(text=f"GPU 온도: {gpu_temp:.1f}°C")

        # --- 그래프 업데이트 ---
        self.draw_cpu_graph()
        self.draw_gpu_graph()

        # 1초마다 반복
        self.after(1000, self.update_loop)

    # =====================================================================
    # CPU 온도 얻기 (히트센서 없는 CPU는 fallback 값 제공)
    # =====================================================================
    def get_cpu_temp(self):
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return 45.0

            # 흔한 키들 중에서 CPU 관련 센서 찾기
            for key, entries in temps.items():
                lname = key.lower()
                if "cpu" in lname or "coretemp" in lname or "amd" in lname:
                    if entries:
                        return float(entries[0].current)
        except Exception:
            pass

        # fallback
        return 45.0

    # =====================================================================
    # GPU 온도 얻기 (외부 콘솔 프로그램 사용 안 함)
    # =====================================================================
    def get_gpu_temp(self):
        now = time.time()

        # 너무 자주 읽지 않도록 3초에 한 번만 센서 접근
        if now - self._last_gpu_read_time < 3.0:
            return self._gpu_temp_cached

        self._last_gpu_read_time = now

        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for key, entries in temps.items():
                    lname = key.lower()
                    # gpu, amdgpu, nv... 등 키워드 포함 센서 찾기
                    if "gpu" in lname or "amdgpu" in lname or "nv" in lname:
                        if entries:
                            self._gpu_temp_cached = float(entries[0].current)
                            return self._gpu_temp_cached
        except Exception:
            pass

        # 센서에서 못 찾으면 기존 값 유지 (최초엔 40.0)
        return self._gpu_temp_cached

    # =====================================================================
    # CPU 그래프
    # =====================================================================
    def draw_cpu_graph(self):
        canvas = self.cpu_canvas
        canvas.delete("all")

        w = 600
        h = 200

        # 사용률 라인
        if len(self.cpu_usage_history) > 1:
            step = w / len(self.cpu_usage_history)
            points = []

            for i, v in enumerate(self.cpu_usage_history):
                x = i * step
                y = h - (v / 100) * h
                points.append((x, y))

            for i in range(len(points) - 1):
                canvas.create_line(points[i], points[i + 1], fill="lime", width=2)

        # 온도 라인
        if len(self.cpu_temp_history) > 1:
            step = w / len(self.cpu_temp_history)
            points = []

            max_temp = max(60, max(self.cpu_temp_history))  # scaling

            for i, t in enumerate(self.cpu_temp_history):
                x = i * step
                y = h - (t / max_temp) * h
                points.append((x, y))

            for i in range(len(points) - 1):
                canvas.create_line(points[i], points[i + 1], fill="red", width=2)

        if self.cpu_usage_history and self.cpu_temp_history:
            canvas.create_text(
                10, 10, anchor="nw", fill="white",
                text=f"CPU 사용률: {self.cpu_usage_history[-1]:.1f}% | CPU 온도: {self.cpu_temp_history[-1]:.1f}°C"
            )

    # =====================================================================
    # GPU 그래프
    # =====================================================================
    def draw_gpu_graph(self):
        canvas = self.gpu_canvas
        canvas.delete("all")

        w = 600
        h = 200

        if len(self.gpu_temp_history) > 1:
            step = w / len(self.gpu_temp_history)
            points = []

            max_temp = max(60, max(self.gpu_temp_history))

            for i, t in enumerate(self.gpu_temp_history):
                x = i * step
                y = h - (t / max_temp) * h
                points.append((x, y))

            for i in range(len(points) - 1):
                canvas.create_line(points[i], points[i + 1], fill="orange", width=2)

        if self.gpu_temp_history:
            canvas.create_text(
                10, 10, anchor="nw", fill="white",
                text=f"GPU 온도(60초): {self.gpu_temp_history[-1]:.1f}°C"
            )
