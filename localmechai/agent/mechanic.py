from __future__ import annotations

from dataclasses import dataclass

from ..models import Finding, HealthReport
from ..storage import latest_report, load_reports
from .repairs import create_confirmation


@dataclass
class AgentAction:
    action_id: str
    title: str
    description: str
    risk: str
    token: str

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "title": self.title,
            "description": self.description,
            "risk": self.risk,
            "token": self.token,
        }


def answer_message(message: str) -> dict:
    report = latest_report()
    history = load_reports(limit=8)
    normalized = message.lower().strip()
    if not normalized:
        normalized = "summarize"

    if report is None and _wants_scan(normalized):
        from ..app import run_scan

        report = run_scan(save=True)
        history = load_reports(limit=8)

    if report is None:
        return {
            "provider": "local-agent",
            "message": "Run a live scan first so I can reason from this machine's real diagnostics.",
            "actions": [],
        }

    if _wants_scan(normalized):
        from ..app import run_scan

        report = run_scan(save=True)
        history = load_reports(limit=8)

    findings = report.analysis.findings
    actions = _suggest_actions(findings, normalized)
    response = _compose_response(report, history, normalized, actions)
    return {
        "provider": "local-agent",
        "message": response,
        "actions": [action.to_dict() for action in actions],
        "latest_report": report.to_dict(),
    }


def _compose_response(
    report: HealthReport, history: list[HealthReport], message: str, actions: list[AgentAction]
) -> str:
    snapshot = report.snapshot
    findings = report.analysis.findings
    severe = [item for item in findings if item.severity in {"warning", "critical"}]
    primary = severe[0] if severe else findings[0]

    if "process" in message or "cpu" in message or "memory" in message:
        top = snapshot.top_processes[:5]
        process_lines = "; ".join(
            f"{proc.name} uses {proc.cpu_percent}% CPU and {proc.memory_mb} MB RAM" for proc in top
        )
        return (
            f"Current load is CPU {snapshot.cpu_percent}% and memory {snapshot.memory_percent}%. "
            f"Top processes: {process_lines}. "
            f"My read: {primary.likely_cause}"
        )

    if "disk" in message or "storage" in message:
        disk_lines = "; ".join(
            f"{disk.mountpoint} is {disk.percent}% full with {disk.free_gb} GB free"
            for disk in snapshot.disks
        )
        return f"Storage check: {disk_lines}. {primary.likely_cause}"

    if "history" in message or "recurring" in message or "again" in message:
        recurring = [finding for finding in findings if finding.code.startswith("recurring_")]
        if recurring:
            names = ", ".join(item.title for item in recurring)
            return f"I see recurring patterns in the saved local reports: {names}. Start with the listed remediation before treating it as normal background noise."
        return f"I checked {len(history)} saved report(s). I do not see a recurring critical pattern beyond the latest findings."

    if actions:
        action_titles = ", ".join(action.title for action in actions)
        return (
            f"The most likely issue is: {primary.title}. {primary.likely_cause} "
            f"I prepared confirmable action(s): {action_titles}. Nothing will run unless you press Confirm."
        )

    return f"{report.analysis.summary} Primary finding: {primary.title}. {primary.likely_cause}"


def _suggest_actions(findings: list[Finding], message: str) -> list[AgentAction]:
    action_ids: list[str] = []
    finding_codes = {finding.code for finding in findings}

    if "clipboard" in message or "copy" in message or "paste" in message:
        action_ids.append("clear_clipboard")
    if "explorer" in message or "taskbar" in message or "desktop" in message:
        action_ids.append("restart_explorer")
    if "windows_update_failure" in finding_codes or "update" in message:
        action_ids.append("open_update_settings")
    if "low_disk_space" in finding_codes or "disk" in message or "storage" in message:
        action_ids.append("open_storage_settings")

    actions: list[AgentAction] = []
    for action_id in dict.fromkeys(action_ids):
        confirmation = create_confirmation(action_id)
        if not confirmation.get("ok"):
            continue
        action = confirmation["action"]
        actions.append(
            AgentAction(
                action_id=action["action_id"],
                title=action["title"],
                description=action["description"],
                risk=action["risk"],
                token=confirmation["token"],
            )
        )
    return actions


def _wants_scan(message: str) -> bool:
    return any(term in message for term in ("scan", "check now", "refresh", "diagnose now"))
