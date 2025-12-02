def _estimate_system_score(specs: dict):
    cpu = specs.get("cpu", {})
    ram = specs.get("ram", {})
    gpus = specs.get("gpus", [])

    cores = cpu.get("physical_cores") or 0
    freq = cpu.get("base_freq_mhz") or 0.0
    cpu_score = cores * (freq / 1000.0)

    ram_score = (ram.get("total_gb") or 0.0) / 4.0

    if gpus:
        gpu = gpus[0]
        vram = gpu.get("memory_total_mb") or 0.0
        gpu_score = vram / 1024.0
    else:
        gpu_score = 1.0

    return cpu_score + ram_score + gpu_score


def recommend(game_name: str, specs: dict, resolution: str, quality: str):
    base_score = _estimate_system_score(specs)

    game_weight = {
        "League of Legends": 0.6,
        "Valorant": 0.7,
        "Overwatch 2": 0.9,
        "PUBG: Battlegrounds": 1.1,
        "AAA High-End": 1.3,
    }.get(game_name, 1.0)

    res_weight = {
        "1920x1080": 1.0,
        "2560x1440": 1.2,
        "3840x2160": 1.6,
    }.get(resolution, 1.0)

    quality_weight = {
        "Low": 0.8,
        "Medium": 1.0,
        "High": 1.2,
        "Ultra": 1.4,
    }.get(quality, 1.0)

    demand = game_weight * res_weight * quality_weight
    perf_index = base_score / (5.0 * demand + 1e-6)

    if perf_index >= 2.0:
        grade = "매우 여유로움"
        fps_range = "100 FPS 이상 예상"
    elif perf_index >= 1.3:
        grade = "원활하게 플레이 가능"
        fps_range = "60 ~ 100 FPS 예상"
    elif perf_index >= 0.8:
        grade = "플레이 가능하지만 옵션 타협 필요"
        fps_range = "40 ~ 60 FPS 예상"
    else:
        grade = "권장 사양 미달"
        fps_range = "40 FPS 미만"

    return {
        "grade": grade,
        "fps_range": fps_range,
        "summary": f"{game_name} / {resolution} / {quality} 기준: {grade} ({fps_range})",
        "perf_index": perf_index,
    }
