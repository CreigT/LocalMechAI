from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


CommandAction = Literal["scan", "latest", "history", "message", "repair"]


class Command(BaseModel):
    action: CommandAction
    token: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class ScanResult(BaseModel):
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str
    system_info: dict[str, Any]
    report: dict[str, Any]


class RepairProposal(BaseModel):
    id: str
    description: str
    risk_level: Literal["low", "medium", "high"]


class AgentResponse(BaseModel):
    status: Literal["success", "rejected", "error"]
    message: str
    result: dict[str, Any] | None = None
