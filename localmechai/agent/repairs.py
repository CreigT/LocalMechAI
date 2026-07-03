from __future__ import annotations

import secrets
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable


@dataclass(frozen=True)
class RepairAction:
    action_id: str
    title: str
    description: str
    risk: str
    command_preview: str
    requires_admin: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RepairToken:
    token: str
    action_id: str
    expires_at: datetime


class RepairRegistry:
    def __init__(self) -> None:
        self._tokens: dict[str, RepairToken] = {}
        self._actions: dict[str, tuple[RepairAction, Callable[[], dict]]] = {
            "clear_clipboard": (
                RepairAction(
                    action_id="clear_clipboard",
                    title="Clear clipboard",
                    description="Clears the current Windows clipboard contents. This can help when copy and paste is stuck.",
                    risk="low",
                    command_preview="Set-Clipboard -Value ''",
                ),
                _clear_clipboard,
            ),
            "restart_explorer": (
                RepairAction(
                    action_id="restart_explorer",
                    title="Restart Windows Explorer",
                    description="Restarts the desktop shell and taskbar. Open File Explorer windows may close.",
                    risk="medium",
                    command_preview="Stop-Process -Name explorer; Start-Process explorer.exe",
                ),
                _restart_explorer,
            ),
            "open_update_settings": (
                RepairAction(
                    action_id="open_update_settings",
                    title="Open Windows Update",
                    description="Opens Windows Update settings so the user can retry updates manually.",
                    risk="low",
                    command_preview="start ms-settings:windowsupdate",
                ),
                _open_update_settings,
            ),
            "open_storage_settings": (
                RepairAction(
                    action_id="open_storage_settings",
                    title="Open Storage settings",
                    description="Opens Windows Storage settings for cleanup review.",
                    risk="low",
                    command_preview="start ms-settings:storagesense",
                ),
                _open_storage_settings,
            ),
        }

    def list_actions(self) -> list[RepairAction]:
        return [item[0] for item in self._actions.values()]

    def get_action(self, action_id: str) -> RepairAction | None:
        item = self._actions.get(action_id)
        return item[0] if item else None

    def create_token(self, action_id: str) -> str:
        if action_id not in self._actions:
            raise KeyError(action_id)
        token = secrets.token_urlsafe(24)
        self._tokens[token] = RepairToken(
            token=token,
            action_id=action_id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        return token

    def execute(self, action_id: str, token: str) -> dict:
        token_record = self._tokens.get(token)
        if token_record is None or token_record.action_id != action_id:
            return {"ok": False, "message": "Confirmation token is invalid. Please request the action again."}
        if token_record.expires_at < datetime.now(timezone.utc):
            self._tokens.pop(token, None)
            return {"ok": False, "message": "Confirmation token expired. Please request the action again."}

        self._tokens.pop(token, None)
        action, runner = self._actions[action_id]
        result = runner()
        result["action"] = action.to_dict()
        return result


def _run_powershell(command: str, timeout: int = 12) -> dict:
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "message": f"Action failed to start: {exc}"}

    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "Action returned a non-zero exit code."
        return {"ok": False, "message": message[:600]}
    return {"ok": True, "message": completed.stdout.strip() or "Action completed."}


def _clear_clipboard() -> dict:
    return _run_powershell("Set-Clipboard -Value ''")


def _restart_explorer() -> dict:
    return _run_powershell(
        "Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue; "
        "Start-Sleep -Milliseconds 700; Start-Process explorer.exe",
        timeout=16,
    )


def _open_update_settings() -> dict:
    return _run_powershell("Start-Process 'ms-settings:windowsupdate'")


def _open_storage_settings() -> dict:
    return _run_powershell("Start-Process 'ms-settings:storagesense'")


REGISTRY = RepairRegistry()


def list_repair_actions() -> list[dict]:
    return [action.to_dict() for action in REGISTRY.list_actions()]


def create_confirmation(action_id: str) -> dict:
    action = REGISTRY.get_action(action_id)
    if action is None:
        return {"ok": False, "message": "Unknown repair action."}
    token = REGISTRY.create_token(action_id)
    return {"ok": True, "token": token, "action": action.to_dict()}


def execute_repair(action_id: str, token: str) -> dict:
    return REGISTRY.execute(action_id, token)
