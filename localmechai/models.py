from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


Severity = Literal["info", "warning", "critical"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    status: str
    username: str | None = None


@dataclass
class DiskInfo:
    mountpoint: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


@dataclass
class ServiceInfo:
    name: str
    status: str


@dataclass
class HealthSnapshot:
    timestamp: str
    platform: str
    boot_time: str
    cpu_percent: float
    cpu_count: int
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    swap_percent: float
    disks: list[DiskInfo]
    top_processes: list[ProcessInfo]
    services: list[ServiceInfo] = field(default_factory=list)
    windows_events: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Finding:
    code: str
    title: str
    severity: Severity
    evidence: list[str]
    likely_cause: str
    remediation: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisResult:
    provider: str
    summary: str
    findings: list[Finding]
    confidence: float
    generated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HealthReport:
    snapshot: HealthSnapshot
    analysis: AnalysisResult

    def to_dict(self) -> dict[str, Any]:
        return {"snapshot": self.snapshot.to_dict(), "analysis": self.analysis.to_dict()}
