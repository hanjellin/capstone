from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QFrame,
)

import traceback

from engine import anomaly_detector


FEATURE_LABELS = {
    "cpu": "CPU 사용률",
    "ram": "RAM 사용률",
    "gpu": "GPU 사용률",
    "gpu_temp": "GPU 온도",
    "disk_read": "디스크 읽기 속도",
    "disk_write": "디스크 쓰기 속도",
    "net_upload": "업로드 속도",
    "net_download": "다운로드 속도",
}


class AnomalyPage(QWidget):
    """
    스파이크 / 이상 탐지 & AI 부하 예측 페이지
    - Autoencoder 기반 이상도(AE) 결과를 카드 형태로 보여준다.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._init_timer()

    # ------------------------------------------------------------------ UI 구성

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 제목
        title = QLabel("실시간 AI 이상 탐지")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # 설명
        desc = QLabel(
            "PC 사용 패턴을 자동으로 학습해, 평소와 다른 이상 징후를 실시간으로 알려줍니다."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555555;")
        layout.addWidget(desc)

        # 상태 카드
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            """
            QFrame {
                background-color: #fdfdfd;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
            """
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        self.status_badge = QLabel("● 비활성화")
        self.status_badge.setStyleSheet("color: #e67e22; font-weight: bold;")
        self.status_text = QLabel("AI 이상 탐지 기능이 아직 준비되지 않았습니다.")
        self.status_text.setStyleSheet("font-weight: bold; font-size: 14px;")

        card_layout.addWidget(self.status_badge)
        card_layout.addWidget(self.status_text)

        self.summary_label = QLabel(
            "학습에 사용할 데이터가 부족하거나, 모델이 아직 학습되지 않았을 수 있습니다."
        )
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("color: #555555;")
        card_layout.addWidget(self.summary_label)

        layout.addWidget(card)

        # 상세 텍스트
        section_title = QLabel("현재 상황 요약")
        section_title.setStyleSheet("font-weight: bold;")
        layout.addWidget(section_title)

        self.detail_edit = QTextEdit()
        self.detail_edit.setReadOnly(True)
        self.detail_edit.setStyleSheet(
            """
            QTextEdit {
                background-color: #fafafa;
                border-radius: 6px;
                border: 1px solid #e0e0e0;
                font-family: '맑은 고딕', sans-serif;
                font-size: 11pt;
            }
            """
        )
        layout.addWidget(self.detail_edit, 1)

        # 하단 안내
        note = QLabel(
            "※ 이 화면은 CPU / 메모리 / 디스크 / 온도 등 여러 정보를 종합해서 "
            "평소와 다른 패턴이 있는지 알려줍니다."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #777777; font-size: 9pt;")
        layout.addWidget(note)

        # 시작 시 기본 상태
        self._set_status_ui(
            color="#e67e22",
            badge_text="● 비활성화",
            status_text="AI 이상 탐지 기능이 아직 준비되지 않았습니다.",
            summary_text="학습에 사용할 데이터가 부족하거나, 모델이 아직 학습되지 않았을 수 있습니다.",
            main_detail=(
                "Autoencoder 모델이 아직 학습되지 않았거나, 임계값 설정 파일이 없습니다.\n\n"
                "PC를 일정 시간 이상 사용해 데이터가 쌓인 뒤 프로그램을 다시 실행하면 "
                "이 화면에서 이상 여부를 자동으로 분석해 줍니다."
            ),
            action_detail="",
        )

    def _set_status_ui(
        self,
        *,
        color: str,
        badge_text: str,
        status_text: str,
        summary_text: str,
        main_detail: str,
        action_detail: str,
    ):
        """상태 배지/텍스트/상세 설명을 한 번에 업데이트."""
        self.status_badge.setText(badge_text)
        self.status_badge.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.status_text.setText(status_text)
        self.summary_label.setText(summary_text)

        detail_lines = [main_detail.strip()]
        if action_detail:
            detail_lines.append("")
            detail_lines.append(action_detail.strip())
        self.detail_edit.setPlainText("\n".join(detail_lines))

    # ------------------------------------------------------------------ 타이머 & 업데이트

    def _init_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(3000)  # 3초마다 갱신
        self.timer.timeout.connect(self._update_anomaly_status)
        self.timer.start()

    def _update_anomaly_status(self):
        """엔진에서 최신 이상 탐지 결과를 가져와 UI를 갱신한다."""
        try:
            result = anomaly_detector.get_latest_anomaly()
        except Exception as e:
            print("[DFY][AE][UI] get_latest_anomaly()에서 예외 발생:", e)
            traceback.print_exc()

            self._set_status_ui(
                color="#e67e22",
                badge_text="● 비활성화",
                status_text="AI 이상 탐지 기능에 문제가 발생했습니다.",
                summary_text="현재는 이상 여부를 분석할 수 없습니다.",
                main_detail="터미널 로그를 확인한 뒤, 문제가 계속되면 개발자에게 문의해 주세요.",
                action_detail="프로그램을 다시 실행하거나 나중에 다시 시도해 주세요.",
            )
            return

        status = result.get("status", "DISABLED")

        if status == "NORMAL":
            color = "#27ae60"
            badge_text = "● 안정적"
            status_text = "현재 패턴은 대체로 안정적입니다."
            summary_text = "평소와 비슷한 자원 사용 패턴이 관측되었습니다."
            main_detail = (
                "AI가 보기에는 현재 CPU / 메모리 / 디스크 / 온도 사용 패턴이 "
                "학습된 정상 범위 안에 있습니다."
            )
            action_detail = "특별히 신경 쓸 부분은 없습니다. 평소처럼 PC를 사용하셔도 됩니다."

        elif status == "WARN":
            color = "#f39c12"
            badge_text = "● 주의 필요"
            status_text = "평소와 다른 사용 패턴이 감지되었습니다."
            summary_text = "가벼운 이상 신호가 관측되었습니다."
            main_detail = (
                "최근 몇 분 동안 일부 자원 사용량이 평소보다 다소 높거나 불안정합니다."
            )
            action_detail = (
                "작업 관리자에서 CPU / 메모리 / 디스크를 많이 쓰는 프로그램이 있는지 확인해 보세요. "
                "불필요한 앱은 종료하는 것이 좋습니다."
            )

        elif status == "CRITICAL":
            color = "#e74c3c"
            badge_text = "● 매우 불안정"
            status_text = "심한 부하 또는 비정상적인 패턴이 감지되었습니다."
            summary_text = "CPU / 메모리 / 디스크 / 온도 중 하나 이상에서 큰 이상이 감지되었습니다."
            main_detail = (
                "AI가 보기에는 최근 패턴이 평소와 크게 다릅니다. "
                "프로세스 폭주나 온도 급상승, 디스크 과부하 등이 의심됩니다."
            )
            action_detail = (
                "작업 관리자에서 사용량이 비정상적으로 높은 프로그램을 우선 확인해 주세요. "
                "필요 없는 앱은 종료하고, 온도가 계속 높다면 잠시 사용을 중단하는 것도 좋습니다."
            )

        elif status == "ERROR":
            color = "#e67e22"
            badge_text = "● 비활성화"
            status_text = "AI 이상 탐지 기능에 문제가 발생했습니다."
            summary_text = "내부 오류로 인해 현재는 이상 여부를 분석할 수 없습니다."
            reason = result.get("reason", "알 수 없는 오류")
            main_detail = (
                "내부 오류로 인해 Autoencoder 결과를 해석하지 못했습니다.\n\n"
                f"reason: {reason}"
            )
            action_detail = "프로그램을 다시 실행하거나, 문제가 계속되면 개발자에게 문의해 주세요."

        elif status == "DISABLED":
            color = "#e67e22"
            badge_text = "● 비활성화"
            status_text = "AI 이상 탐지 기능이 아직 준비되지 않았습니다."
            summary_text = "학습에 사용할 데이터가 부족하거나, 모델이 아직 학습되지 않았을 수 있습니다."
            reason = result.get("reason", "ae_not_available")
            main_detail = (
                "Autoencoder 모델이 아직 학습되지 않았거나, 임계값 설정 파일이 없습니다.\n\n"
                f"reason: {reason}"
            )
            action_detail = (
                "어느 정도 시간 동안 PC를 사용해 데이터가 쌓인 뒤, "
                "프로그램을 다시 실행해 주세요."
            )

        else:
            color = "#e67e22"
            badge_text = "● 비활성화"
            status_text = "AI 이상 탐지 상태를 알 수 없습니다."
            summary_text = "내부 상태 코드가 예상과 다릅니다."
            main_detail = f"status 값이 '{status}'로 표시되었습니다. 내부 로직을 확인해 주세요."
            action_detail = "프로그램을 다시 실행하거나, 문제가 계속되면 개발자에게 문의해 주세요."

        # 주요 변화 항목: WARN / CRITICAL일 때만 UI에 붙이기
        top_devs = result.get("top_deviations") or []
        if status in ("WARN", "CRITICAL") and top_devs:
            lines = []
            for dev in top_devs:
                key = dev.get("key", "")
                label = dev.get("label") or FEATURE_LABELS.get(key, key)
                direction = dev.get("direction", "neutral")
                z = float(dev.get("z", 0.0))

                az = abs(z)
                if az >= 3.0:
                    degree = "매우 크게"
                elif az >= 2.0:
                    degree = "꽤 크게"
                else:
                    degree = "약간"

                if direction == "high":
                    text = f"{label}이(가) 평소보다 {degree} 높습니다."
                elif direction == "low":
                    text = f"{label}이(가) 평소보다 {degree} 낮습니다."
                else:
                    continue

                lines.append("· " + text)

            if lines:
                extra_detail = "주요 변화 항목:\n" + "\n".join(lines)
                main_detail = main_detail + "\n\n" + extra_detail

        self._set_status_ui(
            color=color,
            badge_text=badge_text,
            status_text=status_text,
            summary_text=summary_text,
            main_detail=main_detail,
            action_detail=action_detail,
        )
