from __future__ import annotations

import sys
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ["LOCALMECHAI_AGENT_SERVER"] = "1"

from localmechai.agent import answer_message, execute_repair
from localmechai.app import run_scan
from localmechai.storage import latest_report, load_reports
from shared.protocol import AgentResponse, Command, ScanResult


app = FastAPI(title="LocalMechAI Local Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8765", "http://localhost:8765", "https://localhost"],
    allow_origin_regex=r"https://.*\.netlify\.app",
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "localmechai-agent"}


@app.post("/execute", response_model=AgentResponse)
def execute_command(command: Command) -> AgentResponse:
    try:
        if command.action == "scan":
            report = run_scan(save=True)
            return AgentResponse(status="success", message="Scan completed.", result=report.to_dict())

        if command.action == "latest":
            report = latest_report()
            if report is None:
                return AgentResponse(status="rejected", message="No local report exists yet.")
            return AgentResponse(status="success", message="Latest report loaded.", result=report.to_dict())

        if command.action == "history":
            limit = int(command.parameters.get("limit", 24))
            reports = [report.to_dict() for report in load_reports(limit=limit)]
            return AgentResponse(status="success", message="History loaded.", result={"reports": reports})

        if command.action == "message":
            message = str(command.parameters.get("message") or "")
            return AgentResponse(status="success", message="Agent response generated.", result=answer_message(message))

        if command.action == "repair":
            action_id = str(command.parameters.get("action_id") or "")
            result = execute_repair(action_id, command.token)
            status = "success" if result.get("ok") else "rejected"
            return AgentResponse(status=status, message=str(result.get("message") or ""), result=result)

        return AgentResponse(status="rejected", message="Unknown command action.")
    except Exception as exc:
        return AgentResponse(status="error", message=str(exc))


def _scan_result(report: dict) -> ScanResult:
    snapshot = report["snapshot"]
    findings = report["analysis"].get("findings", [])
    warnings = [finding for finding in findings if finding.get("severity") in {"warning", "critical"}]
    return ScanResult(
        warnings=warnings,
        timestamp=snapshot["timestamp"],
        system_info={
            "platform": snapshot.get("platform"),
            "cpu_percent": snapshot.get("cpu_percent"),
            "memory_percent": snapshot.get("memory_percent"),
            "disks": snapshot.get("disks", []),
        },
        report=report,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8766)
