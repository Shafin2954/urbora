"""Agent runtime configuration, loaded from environment (.env).

PROVIDER: OpenAI (per human A's decision — deviates from PRD §11's Claude/Sonnet
mandate; see LOG1). The agent loop, tools, prompts, and the frozen SSE schema are
provider-neutral; only the backend in llm_client.py is OpenAI-specific.

Model switch is env-var ONLY: set OPENAI_MODEL, restart. Never in a prompt.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # backend/.env if present; no-op otherwise

DEFAULT_MODEL = "gpt-4o-mini"       # tool-capable, cost-appropriate baseline; override via OPENAI_MODEL
DEFAULT_MAX_TOKENS = 4000
DEFAULT_TEMPERATURE = 0.2           # low for deterministic narration; blank env → omit param
DEFAULT_MAX_ITERATIONS = 12         # agent loop guard (NOTES #5, CLAUDE.md rule 9)


def _float_or_none(raw: str | None) -> float | None:
    if raw is None or raw.strip() == "":
        return None
    return float(raw)


@dataclass(frozen=True)
class AgentConfig:
    model: str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float | None = DEFAULT_TEMPERATURE
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    api_key: str | None = None
    base_url: str | None = None

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
            temperature=_float_or_none(
                os.getenv("AGRISENSE_TEMPERATURE", str(DEFAULT_TEMPERATURE))
            ),
            max_iterations=int(
                os.getenv("AGRISENSE_MAX_ITERATIONS", str(DEFAULT_MAX_ITERATIONS))
            ),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )
