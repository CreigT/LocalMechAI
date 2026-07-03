from __future__ import annotations

import platform
import json
import subprocess
import time
from datetime import datetime, timezone

import psutil

from .models import DiskInfo, HealthSnapshot, ProcessInfo, ServiceInfo, now_iso


WATCHED_SERVICES = ("EventLog", "Schedule", "WSearch", "Winmgmt")


def _gb(value: int | float) -> float:
    return round(float(value) / (1024**3), 2)


def _boot_time_iso() -> str:
    return datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc).isoformat()


def collect_disks() -> list[DiskInfo]:
    disks: list[DiskInfo] = []
    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except (PermissionError, OSError):
            continue
        disks.append(
            DiskInfo(
                mountpoint=partition.mountpoint,
                total_gb=_gb(usage.total),
                used_gb=_gb(usage.used),
                free_gb=_gb(usage.free),
                percent=round(float(usage.percent), 1),
            )
        )
    return disks


def collect_processes(limit: int = 12) -> list[ProcessInfo]:
    processes: list[ProcessInfo] = []
    cpu_count = psutil.cpu_count(logical=True) or 1
    tracked = list(psutil.process_iter(["pid", "name", "memory_info", "status", "username"]))
    for proc in tracked:
        try:
            proc.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    time.sleep(0.2)

    for proc in tracked:
        try:
            info = proc.as_dict(attrs=["pid", "name", "memory_info", "status", "username"])
            pid = int(info.get("pid") or 0)
            name = str(info.get("name") or "unknown")
            if pid == 0 or name.lower() == "system idle process":
                continue
            mem = info.get("memory_info")
            cpu_percent = float(proc.cpu_percent(interval=None) or 0.0) / cpu_count
            processes.append(
                ProcessInfo(
                    pid=pid,
                    name=name,
                    cpu_percent=round(cpu_percent, 1),
                    memory_mb=round(float(getattr(mem, "rss", 0)) / (1024**2), 1),
                    status=str(info.get("status") or "unknown"),
                    username=info.get("username"),
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return sorted(processes, key=lambda item: (item.cpu_percent, item.memory_mb), reverse=True)[:limit]


def collect_services() -> list[ServiceInfo]:
    if platform.system().lower() != "windows" or not hasattr(psutil, "win_service_get"):
        return []

    services: list[ServiceInfo] = []
    for service_name in WATCHED_SERVICES:
        try:
            service = psutil.win_service_get(service_name)
            service_info = service.as_dict()
            services.append(ServiceInfo(name=service_name, status=str(service_info.get("status", "unknown"))))
        except Exception:
            services.append(ServiceInfo(name=service_name, status="unavailable"))
    return services


def collect_recent_windows_events(max_events: int = 8) -> list[str]:
    if platform.system().lower() != "windows":
        return []

    query = (
        "Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2; StartTime=(Get-Date).AddDays(-2)} "
        "-MaxEvents "
        f"{max_events} | Select-Object "
        "@{Name='TimeCreated';Expression={$_.TimeCreated.ToString('o')}}, "
        "ProviderName, Id, LevelDisplayName, Message "
        "| ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", query],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    output = completed.stdout.strip()
    if completed.returncode != 0 or not output:
        return []
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return [output[:1000]]

    events = parsed if isinstance(parsed, list) else [parsed]
    summaries: list[str] = []
    for event in events[:max_events]:
        if not isinstance(event, dict):
            continue
        message = str(event.get("Message") or "").replace("\r", " ").replace("\n", " ")
        summaries.append(
            " | ".join(
                [
                    str(event.get("TimeCreated") or "unknown-time"),
                    str(event.get("ProviderName") or "unknown-provider"),
                    f"ID {event.get('Id', 'unknown')}",
                    str(event.get("LevelDisplayName") or "unknown-level"),
                    message[:420],
                ]
            )
        )
    return summaries


def collect_snapshot() -> HealthSnapshot:
    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return HealthSnapshot(
        timestamp=now_iso(),
        platform=f"{platform.system()} {platform.release()} ({platform.version()})",
        boot_time=_boot_time_iso(),
        cpu_percent=round(float(cpu_percent), 1),
        cpu_count=psutil.cpu_count(logical=True) or 0,
        memory_percent=round(float(memory.percent), 1),
        memory_used_gb=_gb(memory.used),
        memory_total_gb=_gb(memory.total),
        swap_percent=round(float(swap.percent), 1),
        disks=collect_disks(),
        top_processes=collect_processes(),
        services=collect_services(),
        windows_events=collect_recent_windows_events(),
    )
