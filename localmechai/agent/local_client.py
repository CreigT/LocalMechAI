from __future__ import annotations

import os
from typing import Any

import requests


DEFAULT_LOCAL_AGENT_URL = "http://127.0.0.1:8766"


def local_agent_enabled() -> bool:
    if os.getenv("LOCALMECHAI_AGENT_SERVER", "").strip() == "1":
        return False
    return os.getenv("LOCALMECHAI_USE_LOCAL_AGENT", "").strip().lower() in {"1", "true", "yes"}


def send_local_agent_command(action: str, parameters: dict[str, Any] | None = None, token: str = "") -> dict | None:
    if not local_agent_enabled():
        return None

    url = os.getenv("LOCALMECHAI_LOCAL_AGENT_URL", DEFAULT_LOCAL_AGENT_URL).rstrip("/")
    try:
        response = requests.post(
            f"{url}/execute",
            json={"action": action, "token": token, "parameters": parameters or {}},
            timeout=8,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None
