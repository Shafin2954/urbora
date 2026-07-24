"""Small, local retrieval layer for the curated Tier 0 agronomy evidence.

This is deliberately deterministic and dependency-free: the indexed corpus is
a hand-curated, individually source-cited set of agronomy passages loaded
from `data/kb/corpus.json` (fertilizer doses, irrigation schedules, pest and
disease treatment, sowing windows — one crop's worth of facts per passage,
not a paragraph mixing everything). The agent supplies English queries,
retrieval ranks matching passages, and the returned text — not model
recall — grounds its explanation (CLAUDE.md rule 2).

Ranking is a stdlib-only TF-IDF-style cosine-ish score: each passage is a
short bag of words, IDF down-weights words that appear in most passages
(the crop name itself, "kg", "ha", ...) and up-weights the words that
actually distinguish one passage from another ("irrigation", "blight",
"tricyclazole", ...). This matters once the corpus has ~50 passages instead
of 5: raw token-overlap counts tie constantly and can't tell "irrigation
schedule" from "irrigation-adjacent mention"; IDF weighting can.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

_CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "kb" / "corpus.json"

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> list[str]:
    return _TOKEN_RE.findall(value.lower())


@lru_cache(maxsize=1)
def _load_docs() -> tuple[dict, ...]:
    """Load + freeze the corpus once per process.

    Each row also gets a precomputed token bag (crop name folded in, so a
    bare crop-name query still matches) so scoring doesn't re-tokenize the
    same passage text on every call.
    """
    with _CORPUS_PATH.open(encoding="utf-8") as f:
        raw = json.load(f)
    docs = []
    for row in raw["passages"]:
        # `topic` (fertilizer/irrigation/pest/disease/sowing/weeding/harvest/
        # climate/calendar) is folded into the searchable text too: the
        # agent's forced queries ("...fertilizer irrigation weed pest
        # checkpoints harvest") are written in exactly this vocabulary, and
        # a passage about aphid control should match a "pest" query even if
        # the word "pest" itself never appears in its prose.
        haystack = (
            f"{row['text']} {row['crop']} {row.get('title', '')} "
            f"{row.get('topic', '')}"
        )
        docs.append({**row, "_tokens": _tokens(haystack)})
    return tuple(docs)


@lru_cache(maxsize=1)
def _idf() -> dict[str, float]:
    """Inverse document frequency over the whole corpus (smoothed)."""
    docs = _load_docs()
    n = len(docs)
    doc_freq: dict[str, int] = {}
    for row in docs:
        for tok in set(row["_tokens"]):
            doc_freq[tok] = doc_freq.get(tok, 0) + 1
    # +1 smoothing keeps the score well-defined and finite even for a token
    # that (future corpus growth aside) appears in every passage.
    return {tok: math.log((n + 1) / (df + 1)) + 1.0 for tok, df in doc_freq.items()}


def _score(query_tokens: list[str], row: dict, idf: dict[str, float]) -> float:
    if not query_tokens:
        return 0.0
    doc_tokens = row["_tokens"]
    if not doc_tokens:
        return 0.0
    doc_tf: dict[str, int] = {}
    for tok in doc_tokens:
        doc_tf[tok] = doc_tf.get(tok, 0) + 1
    matched = set(query_tokens) & set(doc_tokens)
    if not matched:
        return 0.0
    # TF-IDF dot product, normalized by sqrt(doc length) so a long passage
    # doesn't out-rank a short precise one purely by repeating common words.
    raw_score = sum(doc_tf[tok] * idf.get(tok, 1.0) for tok in matched)
    return raw_score / math.sqrt(len(doc_tokens))


def rag_query(query: str, crop: str | None = None, limit: int = 3) -> dict:
    """Retrieve source-cited agronomy passages for an English agent query."""
    if not query.strip():
        return {"error": "query is required"}
    if limit < 1 or limit > 5:
        return {"error": "limit must be between 1 and 5"}

    docs = _load_docs()
    rows = [row for row in docs if crop is None or row["crop"] == crop]
    if crop is not None and not rows:
        return {"error": f"no curated KB record for crop: {crop}"}

    query_tokens = _tokens(query)
    idf = _idf()
    scored = [(_score(query_tokens, row, idf), row) for row in rows]
    scored = [pair for pair in scored if pair[0] > 0] or scored  # fall back to
    # unscored rows only if literally nothing matched, so a query with no
    # token overlap still returns the crop's passages rather than nothing.
    ranked = sorted(scored, key=lambda pair: pair[0], reverse=True)[:limit]

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "query": query,
        "crop": crop,
        "matches": [
            {
                "id": row["id"], "crop": row["crop"], "text": row["text"],
                "score": round(score, 4), "source_type": "kb", "source_id": row["id"],
                "source_title": row["source_title"], "locator": row["locator"],
                "retrieved_at": now, "confidence": row.get("confidence", "medium"),
            }
            for score, row in ranked
        ],
    }
