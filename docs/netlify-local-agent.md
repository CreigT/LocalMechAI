# Netlify + Local Agent Deployment

LocalMechAI now supports a Path 1 deployment model:

- `web-dashboard/` can be deployed to Netlify as the hosted dashboard.
- `local-agent/` runs on the user's Windows PC at `http://127.0.0.1:8766`.
- `shared/` contains the protocol models used between the dashboard and the local agent.
- The original local-only app on `http://127.0.0.1:8765` remains available.

## Local Agent

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start the local agent:

```powershell
python local-agent/agent.py
```

Health check:

```text
http://127.0.0.1:8766/health
```

## Netlify Dashboard

The Netlify publish directory is:

```text
web-dashboard
```

The hosted dashboard calls the local agent at `http://127.0.0.1:8766`. If the local agent is not running, the dashboard shows a real connection error rather than fake diagnostic data.

## Safety Model

Repairs still require the existing confirmation-token flow. The hosted dashboard can request a repair proposal, but the local agent will only execute allowlisted repairs with a valid short-lived token.
