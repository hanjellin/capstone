import statistics
from datetime import datetime

from . import metrics_buffer
from model.predictor import LoadPredictor


# -------- 스파이크 감지 (통계 기반) --------

def detect_spikes(values, threshold_std=2.5):
    if not values or len(values) < 5:
        return {
            "indices": [],
            "original_mean": None,
            "cleaned_mean": None,
            "cleaned_values": values,
        }

    mean_val = statistics.mean(values)
    std_val = statistics.pstdev(values)

    if std_val == 0:
        return {
            "indices": [],
            "original_mean": mean_val,
            "cleaned_mean": mean_val,
            "cleaned_values": values,
        }

    indices = []
    cleaned = []
    for i, v in enumerate(values):
        if abs(v - mean_val) > threshold_std * std_val:
            indices.append(i)
            cleaned.append(mean_val)
        else:
            cleaned.append(v)

    cleaned_mean = statistics.mean(cleaned) if cleaned else None

    return {
        "indices": indices,
        "original_mean": mean_val,
        "cleaned_mean": cleaned_mean,
        "cleaned_values": cleaned,
    }


# -------- LSTM LoadPredictor --------

_PREDICTOR: LoadPredictor | None = None


def _get_predictor() -> LoadPredictor:
    global _PREDICTOR
    if _PREDICTOR is None:
        _PREDICTOR = LoadPredictor()  # internal/model_load_lstm.pth 필요
        print("[DFY] LoadPredictor 로딩 완료")
    return _PREDICTOR


def assess_load_risk():
    predictor = _get_predictor()
    history = metrics_buffer.get_feature_history()
    if not history:
        return None
    return predictor.assess_risk(history)


# -------- 점수 계산 / 진단 --------

def _score_from_limits(value, warn, danger, reverse=False):
    if value is None:
        return 80

    if not reverse:
        if value >= danger:
            return 20
        elif value >= warn:
            return 50
        else:
            return 90
    else:
        if value <= danger:
            return 20
        elif value <= warn:
            return 50
        else:
            return 90


def run_full_diagnosis(specs: dict, metrics: dict, history_cpu_temp=None):
    if history_cpu_temp is None:
        history_cpu_temp = []

    issues = []
    score_parts = []

    cpu_temp = metrics.get("cpu_temp")
    gpu_temp = metrics.get("gpu_temp")
    cpu_usage = metrics.get("cpu_usage")
    ram_usage = metrics.get("ram_usage")
    disk_usage = metrics.get("disk_usage")

    # 1) 기본 자원 상태 점수
    cpu_temp_score = _score_from_limits(cpu_temp, warn=80, danger=90, reverse=False)
    score_parts.append(cpu_temp_score)
    if cpu_temp is not None and cpu_temp >= 80:
        issues.append(f"CPU 온도가 높습니다 ({cpu_temp:.1f}℃). 쿨링 상태를 점검해 주세요.")

    if gpu_temp is not None:
        gpu_temp_score = _score_from_limits(gpu_temp, warn=80, danger=90, reverse=False)
        score_parts.append(gpu_temp_score)
        if gpu_temp >= 80:
            issues.append(f"GPU 온도가 높습니다 ({gpu_temp:.1f}℃). 팬/통풍 상태를 점검해 주세요.")
    else:
        score_parts.append(80)

    if ram_usage is not None:
        ram_score = _score_from_limits(ram_usage, warn=80, danger=90, reverse=False)
        score_parts.append(ram_score)
        if ram_usage >= 80:
            issues.append(f"메모리 사용률이 높습니다 ({ram_usage:.1f}%). 불필요한 프로그램 종료를 권장합니다.")
    else:
        score_parts.append(80)

    if disk_usage is not None:
        disk_score = _score_from_limits(disk_usage, warn=85, danger=95, reverse=False)
        score_parts.append(disk_score)
        if disk_usage >= 85:
            issues.append(f"시스템 드라이브 사용량이 높습니다 ({disk_usage:.1f}%). 여유 공간 확보가 필요합니다.")
    else:
        score_parts.append(80)

    # 2) CPU 온도 시계열 스파이크 분석
    spike_info = None
    if history_cpu_temp and len(history_cpu_temp) >= 10:
        spike_info = detect_spikes(history_cpu_temp)
        if spike_info["indices"]:
            issues.append(
                f"최근 CPU 온도에서 급상승 패턴이 {len(spike_info['indices'])}회 감지되었습니다."
            )

    # 3) LSTM 부하 예측 기반 위험도
    load_risk = assess_load_risk()
    if load_risk is not None and load_risk.get("predicted_cpu") is not None:
        status_l = load_risk["status"]
        pred_cpu = load_risk["predicted_cpu"]
        risk_score = load_risk["risk_score"]

        if status_l == "WARN":
            issues.append(
                f"LSTM 부하 예측 결과, 곧 CPU 사용률이 {pred_cpu:.1f}% 수준까지 올라갈 가능성이 있어 주의가 필요합니다."
            )
        elif status_l == "CRITICAL":
            issues.append(
                f"LSTM 부하 예측 결과, 곧 CPU 사용률이 {pred_cpu:.1f}% 수준까지 매우 높아질 것으로 예상됩니다. "
                f"불필요한 작업을 종료하고 냉각 상태를 점검하는 것을 권장합니다."
            )

        penalty = int(risk_score * 10)  # 최대 10점 깎기
        score_parts.append(max(0, 100 - penalty))

    # 4) 최종 점수/상태
    overall_score = int(sum(score_parts) / len(score_parts)) if score_parts else 80

    if overall_score >= 85:
        status = "정상"
    elif overall_score >= 70:
        status = "주의"
    else:
        status = "위험"

    if not issues:
        issues.append("특별한 이상 징후는 감지되지 않았습니다.")

    summary = f"전체 점수: {overall_score}점, 상태: {status}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "timestamp": now,
        "score": overall_score,
        "status": status,
        "summary": summary,
        "issues": issues,
        "metrics": metrics,
        "specs_cpu": specs.get("cpu", {}),
        "specs_ram": specs.get("ram", {}),
        "specs_gpu_count": len(specs.get("gpus", [])),
        "spike_info": spike_info,
        "load_risk": load_risk,
    }
