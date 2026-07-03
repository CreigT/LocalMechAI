# LocalMechAI

LocalMechAI is a local-first Windows system health and diagnostics agent. It scans CPU, memory, disk, processes, and common Windows failure signals, then explains likely root causes and safe remediation steps in plain language.

## What It Does

- Scans CPU, RAM, disk, process, boot, and Windows service health.
- Detects common problems such as memory pressure, high CPU load, low disk space, Explorer instability, clipboard issues, and suspicious resource spikes.
- Uses a local AI provider through Ollama when available.
- Falls back to deterministic local reasoning when no model is configured.
- Saves health snapshots over time for recurring issue tracking.
- Serves a privacy-focused local dashboard.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m localmechai.app scan
python -m localmechai.app serve
```

Then open `http://127.0.0.1:8765`.

## Optional AI Providers

### Ollama

Install Ollama, pull a model, then set:

```powershell
$env:LOCALMECHAI_AI_PROVIDER = "ollama"
$env:LOCALMECHAI_OLLAMA_MODEL = "qwen2.5:7b"
```

### Gemini

Gemini support is scaffolded for users who prefer a cloud model. Set:

```powershell
$env:LOCALMECHAI_AI_PROVIDER = "gemini"
$env:GEMINI_API_KEY = "your-key"
```

The default mode is `auto`, which tries Ollama first and then uses the local fallback.

## Data Location

Reports are stored locally in:

```text
data/reports.jsonl
```

No system data is sent anywhere unless you explicitly configure a non-local AI provider.

## Safety

LocalMechAI recommends repairs but does not run invasive fixes automatically. Remediation steps are intentionally conservative and reversible where possible.
