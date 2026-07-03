from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "LocalMechAI"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_PATH = DATA_DIR / "reports.jsonl"


@dataclass(frozen=True)
class AIConfig:
    provider: str
    ollama_url: str
    ollama_model: str
    gemini_api_key: str | None
    gemini_model: str


def load_ai_config() -> AIConfig:
    return AIConfig(
        provider=os.getenv("LOCALMECHAI_AI_PROVIDER", "auto").strip().lower(),
        ollama_url=os.getenv("LOCALMECHAI_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/"),
        ollama_model=os.getenv("LOCALMECHAI_OLLAMA_MODEL", "qwen2.5:7b"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("LOCALMECHAI_GEMINI_MODEL", "gemini-1.5-flash"),
    )
