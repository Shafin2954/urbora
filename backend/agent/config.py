"""Agent runtime configuration, loaded from environment (.env).

Model switch is env-var ONLY (PRD §11): change AGRISENSE_MODEL, restart. No
model choice ever lives in a prompt or gets decided by the LLM.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # backend/.env if present; no-op otherwise

DEFAULT_MODEL = "claude-sonnet-5"        # primary: cost-appropriate, native tool use, 1M ctx
DEFAULT_MAX_TOKENS = 8000
DEFAULT_EFFORT = "medium"                # low|medium|high|xhigh|max
DEFAULT_MAX_ITERATIONS = 12              # agent loop guard (NOTES #5, CLAUDE.md rule 9)
DEFAULT_THINKING = "adaptive"            # adaptive|off


@dataclass(frozen=True)
class AgentConfig:
    model: str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    effort: str = DEFAULT_EFFORT
    thinking: str = DEFAULT_THINKING
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    api_key: str | None = None

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            model=os.getenv("AGRISENSE_MODEL", DEFAULT_MODEL),
            max_tokens=int(os.getenv("AGRISENSE_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
            effort=os.getenv("AGRISENSE_EFFORT", DEFAULT_EFFORT),
            thinking=os.getenv("AGRISENSE_THINKING", DEFAULT_THINKING),
            max_iterations=int(
                os.getenv("AGRISENSE_MAX_ITERATIONS", str(DEFAULT_MAX_ITERATIONS))
            ),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
