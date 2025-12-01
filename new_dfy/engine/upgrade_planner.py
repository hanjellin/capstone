def _estimate_cpu_strength(cpu: dict):
    cores = cpu.get("physical_cores") or 0
    freq = cpu.get("base_freq_mhz") or 0.0
    return cores * (freq / 1000.0)


def _estimate_ram_strength(ram: dict):
    return ram.get("total_gb") or 0.0


def _estimate_gpu_strength(gpus: list):
    if not gpus:
        return 0.0
    vram = gpus[0].get("memory_total_mb") or 0.0
    return vram / 1024.0


def generate_plan(specs: dict):
    cpu = specs.get("cpu", {})
    ram = specs.get("ram", {})
    gpus = specs.get("gpus", [])

    cpu_s = _estimate_cpu_strength(cpu)
    ram_s = _estimate_ram_strength(ram)
    gpu_s = _estimate_gpu_strength(gpus)

    parts = {"CPU": cpu_s, "RAM": ram_s, "GPU": gpu_s}
    weakest_part = min(parts, key=parts.get) if parts else None

    lines = []

    lines.append("▶ 1단계: 저비용 / 체감 효율 업그레이드")
    if ram_s < 12:
        lines.append("- 메모리가 부족한 편입니다. 최소 16GB 이상으로 확장을 권장합니다.")
    else:
        lines.append("- 메모리는 현재 수준에서도 크게 부족하지 않습니다.")
    lines.append("- 시스템 디스크 여유 공간을 확보하고, 불필요한 프로그램을 정리해 주세요.")
    lines.append("")

    lines.append("▶ 2단계: 게이밍 성능 향상")
    if weakest_part == "GPU":
        lines.append("- 현재 시스템에서 가장 병목이 되는 부분은 GPU로 추정됩니다.")
        lines.append("- 예산에 맞는 상위 GPU로의 업그레이드를 우선적으로 고려해 보세요.")
    else:
        lines.append("- GPU 성능은 상대적으로 나쁘지 않습니다만, 고주사율/고해상도 게이밍에는 업그레이드가 도움이 됩니다.")
    lines.append("")

    lines.append("▶ 3단계: 플랫폼 변경 / 장기 플랜")
    if cpu_s < 8:
        lines.append("- CPU 성능이 다소 낮은 편입니다. 차후 메인보드, CPU, 메모리를 함께 교체하는 플랫폼 업그레이드를 고려해 보세요.")
    else:
        lines.append("- CPU 성능은 일정 수준 이상이지만, 차세대 플랫폼으로 전환 시 전반적인 성능과 전력 효율 향상을 기대할 수 있습니다.")
    lines.append("- 파워, 쿨링, 케이스 에어플로우 등도 함께 점검해 보면 좋습니다.")

    return "\n".join(lines)
