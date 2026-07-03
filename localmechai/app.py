from __future__ import annotations

import argparse
import json

from .ai import analyze_snapshot
from .config import DEFAULT_HOST, DEFAULT_PORT
from .diagnostics import collect_snapshot
from .models import HealthReport
from .storage import load_reports, save_report


def run_scan(save: bool = True) -> HealthReport:
    history = load_reports(limit=12)
    snapshot = collect_snapshot()
    analysis = analyze_snapshot(snapshot, history)
    report = HealthReport(snapshot=snapshot, analysis=analysis)
    if save:
        save_report(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(prog="localmechai", description="Local Windows health diagnostics.")
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Run a health scan.")
    scan_parser.add_argument("--no-save", action="store_true", help="Print the report without saving it.")

    serve_parser = subparsers.add_parser("serve", help="Start the local dashboard.")
    serve_parser.add_argument("--host", default=DEFAULT_HOST)
    serve_parser.add_argument("--port", default=DEFAULT_PORT, type=int)

    args = parser.parse_args()
    if args.command == "serve":
        from .server import run_server

        run_server(host=args.host, port=args.port)
        return

    report = run_scan(save=not getattr(args, "no_save", False))
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
