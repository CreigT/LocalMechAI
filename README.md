# LocalMechAI

A **local-first Windows system health and diagnostics agent** that scans CPU, memory, disk, processes, boot health, Windows services, and common failure signals, then explains likely causes and conservative remediation steps in plain language.

LocalMechAI is designed around privacy, human approval, and safe diagnostics. It can use Ollama locally, fall back to deterministic reasoning, or optionally use a configured cloud AI provider.

## What It Does

- Scans CPU, RAM, disk, process, boot, and Windows service health
- Detects memory pressure, high CPU load, low disk space, Explorer instability, clipboard issues, and suspicious resource spikes
- Uses a local AI provider through Ollama when available
- Falls back to deterministic local reasoning when no model is configured
- Saves health snapshots for recurring issue tracking
- Serves a privacy-focused local dashboard
- Keeps repair actions behind explicit user confirmation

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m localmechai.app scan
python -m localmechai.app serve
```

Then open `http://127.0.0.1:8765`.

## AI Providers

### Local / Default

LocalMechAI can operate without a cloud model using deterministic local reasoning.

### Ollama

```powershell
$env:LOCALMECHAI_AI_PROVIDER = "ollama"
$env:LOCALMECHAI_OLLAMA_MODEL = "qwen2.5:7b"
```

The default `auto` mode tries Ollama first and then uses the local fallback.

### Google ADK Agent

```powershell
pip install -e .[adk]
```

The application exposes only allowlisted repair actions, and every repair requires explicit confirmation in the dashboard before execution.

### Gemini

```powershell
$env:LOCALMECHAI_AI_PROVIDER = "gemini"
$env:GEMINI_API_KEY = "your-key"
```

Configuring a cloud provider changes the privacy boundary. Review what information will be transmitted before enabling one.

## Data and Privacy

Reports are stored locally in:

```text
data/reports.jsonl
```

No system data is intended to leave the machine unless the user explicitly configures a non-local AI provider or another external integration.

## Safety Model

LocalMechAI is intentionally conservative:

- Diagnosis does not automatically authorize remediation
- Repair actions are allowlisted
- Repairs require explicit user confirmation
- Recommendations should favor reversible actions
- High-impact system changes should fail closed rather than execute without authorization

## Netlify + Local Agent Architecture

The repository also contains a hosted-dashboard/local-agent model:

- `web-dashboard/` — hosted dashboard files
- `local-agent/` — Windows agent running at `127.0.0.1:8766`
- `shared/` — command, scan, and repair protocol
- `netlify.toml` — Netlify publishing configuration

See `docs/netlify-local-agent.md` for the deployment model.

## Security

Do not commit API keys or credentials. Cloud-provider keys should be supplied through environment variables or an appropriate secrets manager.

The local agent should remain bound to localhost unless a separate authenticated and encrypted remote-access design is intentionally implemented.

## Verification

Before treating a build as production-ready, verify installation, scan behavior, dashboard operation, AI-provider fallback, repair confirmation gates, and failure handling on a supported Windows environment.

## Project Status

**Active development / portfolio project.**

LocalMechAI demonstrates the combination of AI-assisted diagnostics, local-first architecture, cybersecurity controls, and human-approved automation.

---

**Sponsored by CREIGNIFICENT LLC.**
