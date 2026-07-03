from __future__ import annotations

from ..app import run_scan
from ..storage import latest_report, load_reports
from .repairs import create_confirmation, list_repair_actions


def run_health_scan() -> dict:
    """Run a real local health scan and save it to local history."""
    return run_scan(save=True).to_dict()


def get_latest_report() -> dict | None:
    """Return the latest saved local report."""
    report = latest_report()
    return report.to_dict() if report else None


def get_history(limit: int = 8) -> dict:
    """Return recent saved reports from the local machine."""
    return {"reports": [report.to_dict() for report in load_reports(limit=limit)]}


def get_repair_actions() -> dict:
    """Return allowlisted repair actions that require explicit confirmation."""
    return {"actions": list_repair_actions()}


def request_repair_confirmation(action_id: str) -> dict:
    """Create a short-lived confirmation token for an allowlisted repair action."""
    return create_confirmation(action_id)
