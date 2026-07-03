from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .app import run_scan
from .agent import answer_message, execute_repair
from .config import DEFAULT_HOST, DEFAULT_PORT, PROJECT_ROOT
from .storage import latest_report, load_reports


WEB_ROOT = PROJECT_ROOT / "web"


class LocalMechHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/latest":
            report = latest_report()
            if report is None:
                report = run_scan(save=True)
            self._send_json(report.to_dict())
            return
        if path == "/api/history":
            reports = [report.to_dict() for report in load_reports(limit=24)]
            self._send_json({"reports": reports})
            return
        return super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/scan":
            report = run_scan(save=True)
            self._send_json(report.to_dict())
            return
        if path == "/api/agent/message":
            payload = self._read_json()
            message = str(payload.get("message") or "")
            self._send_json(answer_message(message))
            return
        if path == "/api/agent/repair":
            payload = self._read_json()
            action_id = str(payload.get("action_id") or "")
            token = str(payload.get("token") or "")
            self._send_json(execute_repair(action_id, token))
            return
        self.send_error(404, "Not found")

    def log_message(self, format: str, *args) -> None:
        print(f"[dashboard] {self.address_string()} - {format % args}")

    def _send_json(self, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    server = ThreadingHTTPServer((host, port), LocalMechHandler)
    print(f"LocalMechAI dashboard running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down LocalMechAI dashboard.")
