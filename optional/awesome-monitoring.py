#!/usr/bin/env python3
"""Collect basic host metrics from /proc and append a JSON line to a daily log."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


LOG_DIR = Path(os.environ.get("AWESOME_MONITORING_LOG_DIR", "/var/log"))


def read_loadavg() -> dict[str, float]:
    # /proc/loadavg: "0.12 0.25 0.31 1/234 12345"
    parts = Path("/proc/loadavg").read_text().split()
    return {
        "loadavg_1": float(parts[0]),
        "loadavg_5": float(parts[1]),
        "loadavg_15": float(parts[2]),
    }


def read_meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, raw = line.split(":", 1)
        values[key] = int(raw.strip().split()[0])

    mem_total = values["MemTotal"]
    mem_available = values["MemAvailable"]
    mem_used = mem_total - mem_available
    swap_total = values["SwapTotal"]
    swap_free = values["SwapFree"]
    return {
        "mem_total_kb": mem_total,
        "mem_available_kb": mem_available,
        "mem_used_kb": mem_used,
        "mem_used_percent": round(mem_used * 100 / mem_total, 2) if mem_total else 0.0,
        "swap_used_kb": swap_total - swap_free,
    }


def read_cpu_times() -> dict[str, int]:
    # first line of /proc/stat: cpu user nice system idle iowait irq softirq ...
    fields = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
    numbers = [int(x) for x in fields]
    idle = numbers[3] + (numbers[4] if len(numbers) > 4 else 0)
    total = sum(numbers)
    return {"cpu_idle_jiffies": idle, "cpu_total_jiffies": total}


def read_uptime() -> dict[str, float]:
    uptime_sec, idle_sec = Path("/proc/uptime").read_text().split()
    return {
        "uptime_seconds": float(uptime_sec),
        "idle_seconds": float(idle_sec),
    }


def collect_metrics() -> dict:
    metrics: dict = {"timestamp": int(time.time())}
    metrics.update(read_loadavg())
    metrics.update(read_meminfo())
    metrics.update(read_cpu_times())
    metrics.update(read_uptime())
    return metrics


def log_path_for_today() -> Path:
    # YY-MM-DD-awesome-monitoring.log
    return LOG_DIR / f"{time.strftime('%y-%m-%d')}-awesome-monitoring.log"


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = log_path_for_today()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(collect_metrics(), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
