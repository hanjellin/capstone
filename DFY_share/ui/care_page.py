import tkinter as tk
from tkinter import ttk


class CarePage(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.label_title = ttk.Label(
            self,
            text="AI 케어 센터",
            font=("맑은 고딕", 16, "bold")
        )
        self.label_title.pack(pady=10)

        self.label_summary = ttk.Label(
            self,
            text="실시간 상태와 AI 진단 결과를 바탕으로 케어 가이드를 제공합니다.",
            font=("맑은 고딕", 12)
        )
        self.label_summary.pack(pady=5)

        self.text = tk.Text(self, height=22, width=100, font=("맑은 고딕", 10))
        self.text.pack(pady=10)

    # monitoring: MonitoringPage 객체
    # diag_result: DiagnosisPage.last_result (dict or None)
    def update(self, monitoring, diag_result):
        # 히스토리
        cpu_usage_hist = monitoring.cpu_usage_history
        cpu_temp_hist = monitoring.cpu_temp_history
        gpu_temp_hist = monitoring.gpu_temp_history
        ram_hist = monitoring.ram_history

        def grad(values, window=10):
            if len(values) < window + 1:
                return 0.0
            return values[-1] - values[-1 - window]

        cpu_temp_rise = grad(cpu_temp_hist)
        gpu_temp_rise = grad(gpu_temp_hist)
        cpu_usage_rise = grad(cpu_usage_hist)
        ram_rise = grad(ram_hist)

        cpu_temp_now = cpu_temp_hist[-1] if cpu_temp_hist else 0.0
        gpu_temp_now = gpu_temp_hist[-1] if gpu_temp_hist else 0.0
        cpu_usage_now = cpu_usage_hist[-1] if cpu_usage_hist else 0.0
        ram_now = ram_hist[-1] if ram_hist else 0.0

        risk_class = 0
        if diag_result is not None:
            risk_class = diag_result.get("risk_class", 0)

        lines = []
        lines.append("📋 현재 시스템 상태 요약\n")

        lines.append(f"- CPU 사용량: {cpu_usage_now:.1f}% (10초 변화: {cpu_usage_rise:+.1f}%)")
        lines.append(f"- CPU 온도: {cpu_temp_now:.1f}°C (10초 변화: {cpu_temp_rise:+.1f}°C)")
        lines.append(f"- GPU 온도: {gpu_temp_now:.1f}°C (10초 변화: {gpu_temp_rise:+.1f}°C)")
        lines.append(f"- RAM 사용률: {ram_now:.1f}% (10초 변화: {ram_rise:+.1f}%)")
        lines.append("")

        lines.append("📊 AI 진단 요약")
        if diag_result is None:
            lines.append("- 아직 AI 진단이 수행되지 않았습니다. 상단의 [AI 진단] 버튼을 먼저 실행하세요.\n")
        else:
            rc_text = ["양호", "주의", "위험"][risk_class]
            lines.append(f"- 직전 스냅샷 진단 결과: {rc_text} (risk_class={risk_class})\n")

        lines.append("🩺 권장 케어 플랜\n")

        # CPU 케어
        if cpu_temp_now >= 85 or cpu_temp_rise > 8:
            lines.append("🔴 [CPU 발열 심각]")
            lines.append("  - 케이스 내부 먼지 청소 및 공기 흐름 확보")
            lines.append("  - CPU 쿨러 장착 상태 점검 (헐거짐/이탈 여부 확인)")
            lines.append("  - 써멀 그리스 재도포 고려")
            lines.append("  - 게임/렌더링 시 팬 곡선 조정 or 성능 모드 완화\n")
        elif cpu_temp_now >= 75 or cpu_temp_rise > 4:
            lines.append("🟠 [CPU 발열 주의]")
            lines.append("  - 고부하 작업(게임, 렌더링, 인코딩) 실행 중인지 점검")
            lines.append("  - 백그라운드 과도한 프로세스(브라우저 탭, 런처 등) 정리")
            lines.append("  - 케이스 측면/후면 통풍 상태 확인\n")
        else:
            lines.append("🟢 [CPU 온도]")
            lines.append("  - 현재 CPU 온도는 안정적인 편입니다.\n")

        # GPU 케어
        if gpu_temp_now >= 85 or gpu_temp_rise > 8:
            lines.append("🔴 [GPU 과열 위험]")
            lines.append("  - 그래픽 카드 팬 정상 동작 여부 확인")
            lines.append("  - 케이스 내부 공기 흐름 개선 (흡기/배기 팬 구성 재점검)")
            lines.append("  - 그래픽 옵션(해상도, 품질, 프레임 제한)을 한 단계 낮추는 것을 고려\n")
        elif gpu_temp_now >= 75 or gpu_temp_rise > 4:
            lines.append("🟠 [GPU 발열 주의]")
            lines.append("  - 장시간 게임/3D 작업 시 간헐적으로 휴식 시간 주기")
            lines.append("  - 그래픽 카드 방열판 및 팬에 먼지가 쌓이지 않았는지 확인\n")
        else:
            lines.append("🟢 [GPU 온도]")
            lines.append("  - GPU 온도는 현재 안정적인 범위입니다.\n")

        # RAM 케어
        if ram_now >= 90 or ram_rise > 15:
            lines.append("🔴 [메모리 부족 위험]")
            lines.append("  - 사용하지 않는 프로그램/브라우저 탭을 정리")
            lines.append("  - 작업 관리자에서 메모리 많이 사용하는 프로세스 확인")
            lines.append("  - 자주 발생한다면 RAM 증설(물리 메모리 추가)을 고려\n")
        elif ram_now >= 75 or ram_rise > 10:
            lines.append("🟠 [메모리 사용량 높음]")
            lines.append("  - 백그라운드 런처(게임 런처, 메신저 등) 정리")
            lines.append("  - 브라우저 탭 수를 줄이거나, 영상/스트리밍 동시 실행 줄이기\n")
        else:
            lines.append("🟢 [메모리]")
            lines.append("  - 메모리 사용량은 양호한 편입니다.\n")

        # 전체 위험도 기반 종합 조언
        if risk_class >= 2:
            lines.append("🔴 [AI 종합 의견]")
            lines.append("  - 전체 시스템 상태가 '위험' 수준으로 평가되었습니다.")
            lines.append("  - 중요한 작업(과제, 영상 편집, 게임 랭크 등) 전에 재부팅 및 점검을 권장합니다.")
            lines.append("  - 발열 및 저장장치 상태를 중점적으로 확인해 주세요.\n")
        elif risk_class == 1:
            lines.append("🟠 [AI 종합 의견]")
            lines.append("  - 일부 지표에서 경고가 감지되었습니다.")
            lines.append("  - 당장 문제는 아니지만, 발열/메모리/디스크 사용률을 주기적으로 확인해 주세요.\n")
        else:
            lines.append("🟢 [AI 종합 의견]")
            lines.append("  - 현재까지는 위험 요소가 크지 않습니다.")
            lines.append("  - 장시간 고부하 작업 시 발열/소음 수준만 가끔 체크해 주세요.\n")

        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, "\n".join(lines))
