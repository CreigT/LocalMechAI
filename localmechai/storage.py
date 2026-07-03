from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import DATA_DIR, REPORTS_PATH
from .models import AnalysisResult, DiskInfo, Finding, HealthReport, HealthSnapshot, ProcessInfo, ServiceInfo


def save_report(report: HealthReport, path: Path = REPORTS_PATH) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report.to_dict(), ensure_ascii=False) + "\n")


def load_reports(path: Path = REPORTS_PATH, limit: int | None = None) -> list[HealthReport]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if limit is not None:
        lines = lines[-limit:]
    reports: list[HealthReport] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            reports.append(report_from_dict(json.loads(line)))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
    return reports


def latest_report() -> HealthReport | None:
    reports = load_reports(limit=1)
    return reports[-1] if reports else None


def report_from_dict(data: dict[str, Any]) -> HealthReport:
    snapshot_data = data["snapshot"]
    analysis_data = data["analysis"]
    snapshot = HealthSnapshot(
        timestamp=snapshot_data["timestamp"],
        platform=snapshot_data["platform"],
        boot_time=snapshot_data["boot_time"],
        cpu_percent=float(snapshot_data["cpu_percent"]),
        cpu_count=int(snapshot_data["cpu_count"]),
        memory_percent=float(snapshot_data["memory_percent"]),
        memory_used_gb=float(snapshot_data["memory_used_gb"]),
        memory_total_gb=float(snapshot_data["memory_total_gb"]),
        swap_percent=float(snapshot_data["swap_percent"]),
        disks=[DiskInfo(**disk) for disk in snapshot_data.get("disks", [])],
        top_processes=[ProcessInfo(**proc) for proc in snapshot_data.get("top_processes", [])],
        services=[ServiceInfo(**service) for service in snapshot_data.get("services", [])],
        windows_events=list(snapshot_data.get("windows_events", [])),
    )
    analysis = AnalysisResult(
        provider=analysis_data["provider"],
        summary=analysis_data["summary"],
        findings=[Finding(**finding) for finding in analysis_data.get("findings", [])],
        confidence=float(analysis_data.get("confidence", 0.0)),
        generated_at=analysis_data.get("generated_at"),
    )
    return HealthReport(snapshot=snapshot, analysis=analysis)
