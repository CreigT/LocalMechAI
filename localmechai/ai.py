from __future__ import annotations

import json
from typing import Any

import requests

from .config import AIConfig, load_ai_config
from .detectors import detect_issues
from .models import AnalysisResult, Finding, HealthReport, HealthSnapshot


SYSTEM_PROMPT = """You are LocalMechAI, a cautious Windows diagnostics assistant.
Use only the supplied system snapshot and findings.
Explain the likely root cause in plain language.
Recommend safe, reversible steps.
Never suggest deleting system folders, disabling security tools, or editing the registry as an early step.
Return concise JSON with keys: summary, confidence."""


def analyze_snapshot(snapshot: HealthSnapshot, history: list[HealthReport] | None = None) -> AnalysisResult:
    config = load_ai_config()
    findings = detect_issues(snapshot, history)

    if config.provider in {"auto", "ollama"}:
        ollama = _try_ollama(config, snapshot, findings)
        if ollama is not None:
            return ollama
        if config.provider == "ollama":
            return _fallback_analysis(findings, "fallback-after-ollama")

    if config.provider == "gemini":
        gemini = _try_gemini(config, snapshot, findings)
        if gemini is not None:
            return gemini
        return _fallback_analysis(findings, "fallback-after-gemini")

    return _fallback_analysis(findings, "local-rules")


def _try_ollama(
    config: AIConfig, snapshot: HealthSnapshot, findings: list[Finding]
) -> AnalysisResult | None:
    payload = {
        "model": config.ollama_model,
        "stream": False,
        "format": "json",
        "prompt": _build_prompt(snapshot, findings),
        "system": SYSTEM_PROMPT,
    }
    try:
        response = requests.post(f"{config.ollama_url}/api/generate", json=payload, timeout=18)
        response.raise_for_status()
        raw = response.json().get("response", "{}")
        parsed = _parse_jsonish(raw)
        summary = str(parsed.get("summary") or _summary_from_findings(findings))
        confidence = float(parsed.get("confidence") or 0.72)
        return AnalysisResult(
            provider=f"ollama:{config.ollama_model}",
            summary=summary,
            findings=findings,
            confidence=max(0.0, min(confidence, 1.0)),
        )
    except Exception:
        return None


def _try_gemini(
    config: AIConfig, snapshot: HealthSnapshot, findings: list[Finding]
) -> AnalysisResult | None:
    if not config.gemini_api_key:
        return None

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.gemini_model}:generateContent?key={config.gemini_api_key}"
    )
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{_build_prompt(snapshot, findings)}"}],
            }
        ],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    try:
        response = requests.post(url, json=payload, timeout=18)
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed = _parse_jsonish(text)
        return AnalysisResult(
            provider=f"gemini:{config.gemini_model}",
            summary=str(parsed.get("summary") or _summary_from_findings(findings)),
            findings=findings,
            confidence=float(parsed.get("confidence") or 0.7),
        )
    except Exception:
        return None


def _fallback_analysis(findings: list[Finding], provider: str) -> AnalysisResult:
    critical_count = sum(1 for item in findings if item.severity == "critical")
    warning_count = sum(1 for item in findings if item.severity == "warning")
    if critical_count:
        summary = f"{critical_count} critical issue(s) need attention. Start with the highest resource or disk warning."
    elif warning_count:
        summary = f"{warning_count} warning(s) detected. The system is usable, but these items may explain slowness."
    else:
        summary = "No urgent issues were detected. Current metrics look healthy."
    return AnalysisResult(provider=provider, summary=summary, findings=findings, confidence=0.66)


def _build_prompt(snapshot: HealthSnapshot, findings: list[Finding]) -> str:
    compact_snapshot = snapshot.to_dict()
    compact_snapshot["windows_events"] = compact_snapshot.get("windows_events", [])[:2]
    return json.dumps(
        {
            "snapshot": compact_snapshot,
            "detected_findings": [finding.to_dict() for finding in findings],
            "task": "Summarize likely root cause and confidence.",
        },
        ensure_ascii=False,
    )


def _parse_jsonish(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        return {}


def _summary_from_findings(findings: list[Finding]) -> str:
    if not findings:
        return "No diagnostics findings were produced."
    primary = findings[0]
    return f"{primary.title}: {primary.likely_cause}"
