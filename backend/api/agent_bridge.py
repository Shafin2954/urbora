"""Run A's synchronous agent loop inside B's async SSE endpoint.

`backend.agent.loop.run_turn` is a plain generator that makes blocking HTTP
calls to the LLM provider and to the weather/geocode tools. Iterating it
directly inside the async endpoint would block the event loop for the whole
turn: heartbeats would stop, `request.is_disconnected()` would never be
checked, and every other request to the process would queue behind one
farmer's plan. So it runs on a worker thread and its events are handed back
over a queue.

This is deliberately a thin adapter and not a redesign of A's loop. A sync
generator is the right shape for the agent (it is straight-line code with tool
calls in the middle); turning it async would mean an async LLM client, async
tools, and a rewrite across an ownership boundary — for no behavioural gain.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

# Sentinel: the producer thread finished. A dedicated object rather than None,
# because None is a legitimate thing to yield.
_END = object()


async def stream_sync_generator(
    factory: Callable[[], Iterator[Any]],
) -> AsyncIterator[Any]:
    """Yield items from a blocking generator without blocking the event loop.

    `factory` is called on the worker thread, not here, so that even the
    generator's construction (and any exception it raises immediately — a
    signature mismatch, a missing API key) happens off the loop and is
    reported through the same channel as everything else.

    Exceptions from the generator are re-raised in the consuming task, so the
    caller can turn them into an honest `error` event instead of a truncated
    stream that looks like a network glitch.

    When the consumer stops early — a farmer locking their phone mid-plan — the
    stop flag is set and the producer exits at the next yield. It cannot be
    interrupted mid-HTTP-call, so one in-flight provider request may still
    complete; that is the cost of a blocking client and it is bounded by that
    one call.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Any] = asyncio.Queue()
    stop = threading.Event()

    def emit(item: Any) -> None:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, item)
        except RuntimeError:
            # The loop is already closed — the consumer is long gone and there
            # is nobody left to tell. Not worth a thread traceback.
            pass

    def produce() -> None:
        generator: Iterator[Any] | None = None
        try:
            generator = factory()
            for item in generator:
                if stop.is_set():
                    break
                emit(item)
        except BaseException as exc:  # noqa: BLE001 — forwarded, not swallowed
            emit(exc)
        finally:
            try:
                # Runs the generator's own `finally` blocks (A's loop prints its
                # cost line there) rather than abandoning it mid-frame. Guarded
                # by getattr because not every iterator is a generator, and an
                # AttributeError here would skip the sentinel below and hang the
                # consumer forever waiting for an event that never comes.
                close = getattr(generator, "close", None)
                if close is not None:
                    close()
            finally:
                emit(_END)

    worker = threading.Thread(target=produce, name="agent-turn", daemon=True)
    worker.start()

    try:
        while True:
            item = await queue.get()
            if item is _END:
                return
            if isinstance(item, BaseException):
                raise item
            yield item
    finally:
        stop.set()
