"""Import-integrity smoke: every backend module loads under the `backend.*`
package layout (no API calls, no network)."""


def test_schemas_import():
    from backend import schemas  # noqa: F401
    from backend.schemas import Provenance, SSEEvent, DoneEvent  # noqa: F401


def test_agent_import():
    from backend.agent import AgentConfig, LLMClient, to_openai_tools  # noqa: F401
    from backend.agent.prompts import SYSTEM_PROMPT
    from backend.agent.tools_spec import TOOL_DEFS, dispatch  # noqa: F401
    from backend.agent.loop import run_turn, run_turn_sync  # noqa: F401
    import inspect
    assert inspect.isasyncgenfunction(run_turn)  # matches backend/api/chat.py's contract
    assert inspect.isgeneratorfunction(run_turn_sync)

    assert SYSTEM_PROMPT.strip()
    assert {t["name"] for t in TOOL_DEFS} == {
        "geocode", "get_forecast", "get_climatology", "cropdb_sql", "crop_scorer",
    }


def test_dispatch_unknown_tool_is_safe():
    from backend.agent.tools_spec import dispatch

    assert "error" in dispatch("no_such_tool", {})


def test_memory_import():
    from backend.memory import (  # noqa: F401
        get_farm,
        get_session_messages,
        save_farm,
        save_session_messages,
    )
