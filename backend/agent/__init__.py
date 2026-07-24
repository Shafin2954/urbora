"""Agent: loop, prompts, orchestration, LLM client (Instance A).

Provider is OpenAI (behind the ChatBackend interface). See llm_client.py.
"""

from .config import AgentConfig
from .llm_client import ChatBackend, LLMClient, OpenAIClient, to_openai_tools

__all__ = ["AgentConfig", "ChatBackend", "LLMClient", "OpenAIClient", "to_openai_tools"]
