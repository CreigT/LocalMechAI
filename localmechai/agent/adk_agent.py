from __future__ import annotations

from . import tools


INSTRUCTION = """You are LocalMechAI's AI Mechanic inside a local Windows diagnostics app.
Use only the app's scanner, history, and repair tools as evidence.
Explain issues plainly and recommend safe next steps.
Never claim a repair has run unless the repair endpoint reports success.
Repairs must always be user-confirmed through the app confirmation button.
Do not recommend deleting Windows, Program Files, user documents, registry keys, or security tools."""


def build_root_agent():
    try:
        from google.adk.agents import Agent
    except Exception:
        return None

    return Agent(
        name="localmechai_mechanic",
        model="gemini-1.5-flash",
        description="Local Windows system health and diagnostics mechanic.",
        instruction=INSTRUCTION,
        tools=[
            tools.run_health_scan,
            tools.get_latest_report,
            tools.get_history,
            tools.get_repair_actions,
            tools.request_repair_confirmation,
        ],
    )


root_agent = build_root_agent()
