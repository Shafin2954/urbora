"""Trace redactor tests (CLAUDE.md §2.12, docs/NOTES.md #19).

The payload shapes here are copied from docs/channels/BDAPPS-API-REFERENCE.md §6.3 / §5, not
invented, so a change in the real request body shape shows up as a test failure
rather than as a credential on a projector.

Run from the repo root:  .venv/Scripts/python -m pytest backend/tests -q
"""

from backend.api import sse
from backend.api.redact import mask_phone, redact

# --- the payload that actually matters -------------------------------------
# docs/channels/BDAPPS-API-REFERENCE.md §6.3, direct debit. Auth rides in the body.
BDAPPS_DEBIT = {
    "externalTrxId": "25609",
    "amount": "5",
    "applicationId": "APP_000123",
    "password": "9f8e7d6c5b4a39281706f5e4d3c2b1a0",
    "subscriberId": "tel:8801812345678",
    "paymentInstrumentName": "Mobile Account",
    "currency": "BDT",
}


def test_bdapps_debit_credentials_never_survive():
    safe, paths = redact(BDAPPS_DEBIT)

    assert safe["password"] == "***"
    assert safe["applicationId"] == "***"
    assert safe["subscriberId"] == "***678"

    # The whole point: the secret must not appear anywhere in the output, in
    # any form. Checking the field alone would miss a copy elsewhere.
    assert "9f8e7d6c5b4a39281706f5e4d3c2b1a0" not in repr(safe)
    assert "8801812345678" not in repr(safe)

    # Judge-relevant values must survive — redaction that eats the amount
    # would break explainability (10 pts) to fix a problem we don't have.
    assert safe["amount"] == "5"
    assert safe["currency"] == "BDT"
    assert safe["externalTrxId"] == "25609"

    assert set(paths) == {"applicationId", "password", "subscriberId"}


def test_input_is_not_mutated():
    """The payments client still needs the real values after we trace them."""
    original = dict(BDAPPS_DEBIT)
    redact(BDAPPS_DEBIT)
    assert BDAPPS_DEBIT == original


def test_nested_and_listed_secrets():
    payload = {
        "request": {"auth": {"password": "hunter2", "applicationId": "APP_1"}},
        "destinationAddresses": ["tel:8801812345678", "tel:8801999999999"],
        "batch": [{"token": "abc123"}, {"apiKey": "def456"}],
    }
    safe, paths = redact(payload)

    # An outer key that matches takes the whole subtree with it.
    assert safe["request"]["auth"] == "***"
    assert "hunter2" not in repr(safe)
    assert safe["destinationAddresses"] == ["***678", "***999"]
    assert safe["batch"][0]["token"] == "***"
    assert safe["batch"][1]["apiKey"] == "***"
    assert "request.auth" in paths


def test_secrets_in_url_query_strings():
    """A key in a URL is the same leak by another route."""
    safe, paths = redact({"url": "https://example.com/v1?lat=24.37&api_key=SEKRIT&lon=88.6"})
    assert "SEKRIT" not in safe["url"]
    assert "lat=24.37" in safe["url"]  # real params still readable
    assert paths == ["url"]


def test_keywords_is_not_mistaken_for_a_key():
    """`key` matches as a whole word only.

    rag_query plausibly takes `keywords`; redacting it would blank a
    judge-relevant param to defend against nothing.
    """
    safe, paths = redact({"keywords": "boro rice fertilizer dose", "monkey": "n/a"})
    assert safe["keywords"] == "boro rice fertilizer dose"
    assert safe["monkey"] == "n/a"
    assert paths == []


def test_bare_key_field_is_redacted():
    """Spec is /key|token|secret/i, so a bare `key` field is masked.

    KNOWN COLLISION, flagged to A: crop.db's `meta` table has a column literally
    named `key` (docs/product/PRD.md §5). If meta rows are surfaced through a tool result
    they will come out as `***`. Fix on A's side is `SELECT key AS meta_key`.
    Tested here so the behaviour is documented rather than discovered.
    """
    safe, _ = redact({"key": "generated_at", "value": "2026-07-24T09:00:00Z"})
    assert safe["key"] == "***"
    assert safe["value"] == "2026-07-24T09:00:00Z"


def test_mask_phone_shapes():
    assert mask_phone("tel:8801812345678") == "***678"
    assert mask_phone("01812345678") == "***678"
    assert mask_phone(8801812345678) == "***678"
    assert mask_phone("12") == "***"  # nothing safe to reveal
    assert mask_phone("") == "***"


def test_non_string_scalars_pass_through():
    """Weather and finance numbers must arrive intact and typed."""
    safe, paths = redact({"temp_c": 31.4, "rain_mm": 0, "ok": True, "missing": None})
    assert safe == {"temp_c": 31.4, "rain_mm": 0, "ok": True, "missing": None}
    assert paths == []


# --- redaction is structural, not remembered --------------------------------


def test_tool_call_event_redacts_by_construction():
    event = sse.tool_call("call_1", "bdapps_debit", BDAPPS_DEBIT)

    assert event["type"] == "tool_call"
    assert event["params"]["password"] == "***"
    assert event["params"]["subscriberId"] == "***678"
    assert "9f8e7d6c5b4a39281706f5e4d3c2b1a0" not in repr(event)
    assert event["redacted"] == ["applicationId", "password", "subscriberId"]


def test_tool_result_event_redacts_by_construction():
    raw = {"statusCode": "S1000", "internalTrxId": "913080108430074",
           "subscriberId": "tel:8801812345678"}
    event = sse.tool_result("call_1", "bdapps_debit", raw)

    assert event["result_raw"]["subscriberId"] == "***678"
    assert event["result_raw"]["statusCode"] == "S1000"  # judges need this
    assert "8801812345678" not in repr(event)


def test_redacted_event_survives_sse_encoding():
    """The last line of defence: what actually goes on the wire is clean."""
    frame = sse.format_sse(sse.tool_call("c1", "bdapps_debit", BDAPPS_DEBIT))
    assert "9f8e7d6c5b4a39281706f5e4d3c2b1a0" not in frame
    assert "8801812345678" not in frame
    assert frame.startswith("data: ")
    assert frame.endswith("\n\n")
