"""Trace redaction.

The trace panel shows judges the raw params and raw results of every tool call
(CLAUDE.md §2.5). bdapps carries its auth *in the request body* — every
`/caas/direct/debit` call contains `applicationId` and a 32-char `password` —
so "show the raw body" and "don't leak credentials" collide head-on. This
module is where that collision is resolved, once, in one place.

Rules (docs/NOTES.md #19, CLAUDE.md §2.5):
  - password / appId / key / token / secret   -> "***"
  - phone / subscriberId                       -> last 3 digits only

Two design choices worth defending:

1. **Redaction is by construction, not by discipline.** The `tool_call` /
   `tool_result` event constructors in sse.py run everything through here, so
   there is no code path that emits an un-redacted trace event. A rule you have
   to remember to apply is a rule you will forget at 4am.

2. **Redactions are reported, not silent.** Every masked field's path comes
   back in `redacted_paths`. A false positive is then *visible* — you can see
   that a field was masked and why — instead of a judge quietly reading `***`
   where a real number should be. It also lets the UI say "3 fields redacted",
   which shows the security was deliberate rather than accidental.
"""

import re
from typing import Any

REDACTED = "***"

# Bare "key" is matched only as a whole word (or _/-/. separated component), so
# `keywords` — a plausible rag_query param — survives, while `key`, `api_key`
# and `apiKey` do not. Lowercasing before matching handles camelCase.
_SECRET_KEY_RE = re.compile(
    r"""
      password | passwd | secret | token | credential | auth
    | app(?:lication)?_?id
    | api_?keys? | access_?keys? | private_?keys?
    | (?:^|[_\-.])keys?(?:$|[_\-.])
    """,
    re.VERBOSE,
)

# Phone-ish fields keep their last 3 digits so a human can still confirm "yes,
# that's the SIM I topped up" without the full number reaching the screen.
_PHONE_KEY_RE = re.compile(
    r"subscriber_?id|msisdn|phone|mobile|source_?address|destination_?addresses?",
)

# Credentials also travel inside URL query strings. Open-Meteo needs no key
# today, but a trace that prints `?apikey=...` is the same leak by another
# route, so strings get scrubbed too.
_URL_SECRET_RE = re.compile(
    r"((?:password|passwd|secret|token|api_?key|access_?key|key|auth)=)([^&\s\"']+)",
    re.IGNORECASE,
)


def _looks_secret(key: str) -> bool:
    return bool(_SECRET_KEY_RE.search(key.lower()))


def _looks_phone(key: str) -> bool:
    return bool(_PHONE_KEY_RE.search(key.lower()))


def mask_phone(value: Any) -> str:
    """Keep the last 3 digits: 'tel:8801812345678' -> '***678'.

    Anything with 3 or fewer digits becomes '***' outright — there is no
    partial reveal that is safe when there is barely anything to reveal.
    """
    digits = re.sub(r"\D", "", str(value))
    if len(digits) <= 3:
        return REDACTED
    return f"{REDACTED}{digits[-3:]}"


def _scrub_url_secrets(text: str) -> str:
    return _URL_SECRET_RE.sub(lambda m: f"{m.group(1)}{REDACTED}", text)


def redact(value: Any) -> tuple[Any, list[str]]:
    """Recursively redact a params/result structure.

    Returns (redacted_copy, sorted_paths_that_were_masked). The input is never
    mutated — the agent loop and the payments client keep their real values;
    only what goes on the wire is masked.
    """
    paths: list[str] = []

    def walk(node: Any, path: str) -> Any:
        if isinstance(node, dict):
            out = {}
            for key, sub in node.items():
                child = f"{path}.{key}" if path else str(key)
                if _looks_secret(str(key)):
                    # Whole subtree goes, whatever shape it is. A nested
                    # {"auth": {"password": ...}} must not survive because the
                    # outer key alone matched.
                    out[key] = REDACTED
                    paths.append(child)
                elif _looks_phone(str(key)):
                    if isinstance(sub, (list, tuple)):
                        out[key] = [mask_phone(item) for item in sub]
                    else:
                        out[key] = mask_phone(sub)
                    paths.append(child)
                else:
                    out[key] = walk(sub, child)
            return out

        if isinstance(node, (list, tuple)):
            return [walk(item, f"{path}[{i}]") for i, item in enumerate(node)]

        if isinstance(node, str):
            scrubbed = _scrub_url_secrets(node)
            if scrubbed != node:
                paths.append(path)
            return scrubbed

        return node

    redacted = walk(value, "")
    return redacted, sorted(set(paths))
