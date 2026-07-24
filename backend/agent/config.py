"""Agent runtime configuration, loaded from environment (.env).

PROVIDER: OpenAI (per human A's decision — deviates from PRD §11's Claude/Sonnet
mandate; see LOG1). The agent loop, tools, prompts, and the frozen SSE schema are
provider-neutral; only the backend in llm_client.py is OpenAI-specific.

Model switch is env-var ONLY: set OPENAI_MODEL, restart. Never in a prompt.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env explicitly — a bare load_dotenv() from the repo root would look
# for ./.env and miss it. Then fall back to the default search (repo-root .env /
# real env vars); load_dotenv never overrides an already-set var.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
load_dotenv()

DEFAULT_MODEL = "gpt-4o"            # tool-calling must be reliable under this 14-tool
# loop + long system prompt. gpt-4o-mini was the original baseline but was
# verified live (2026-07-25) to skip tool calls entirely on a dense intake
# message — zero tool_call events, model answered from recall instead. gpt-4o
# was verified working on this account (ask_farmer fired correctly). Override
# via OPENAI_MODEL if your account has something better; see backend/.env.example.
DEFAULT_MAX_TOKENS = 4000
DEFAULT_TEMPERATURE = 0.0           # deterministic narration AND deterministic tool-call
# decisions. Live-verified 2026-07-25: at 0.2, gpt-4o was flaky on a vague opening
# message — sometimes called ask_farmer (correct), sometimes answered the same
# missing-district question in plain chat text instead (the bug rule this whole
# section exists to prevent). 0.0 is the lowest lever available before touching
# the prompt further; blank env → omit param (for reasoning models that reject it).
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
