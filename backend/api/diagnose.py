"""Leaf-photo disease detection route (competition.md Tier 2).

    POST /api/diagnose/image   multipart form, field name `file`
    GET  /api/diagnose/status  is the model loadable on this machine?

The heavy work is in `backend/tools/leaf_diagnosis.py`; this file is only the
HTTP edge. The status route exists so the UI can hide the camera button on a
deployment where torch was never installed, rather than offering an upload that
is going to fail — the same rule the microphone follows in the frontend.

Not registered as an agent tool. The model consumes an image, and the agent's
tool-call channel carries JSON; the farmer uploads a photo, gets a classification
with its disclosures, and can then ASK about the named disease through the normal
chat path, where `rag_query` answers with cited treatment text. Routing an image
through the tool loop would buy nothing and would put a base64 blob in the trace.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.tools.leaf_diagnosis import diagnose_leaf

router = APIRouter()

# A phone photo is comfortably under this; anything larger is a mistake or an
# attempt to exhaust memory, and either way the farmer should hear about it
# rather than wait for a timeout.
_MAX_BYTES = 8 * 1024 * 1024


@router.get("/api/diagnose/status")
async def diagnose_status() -> dict:
    """Whether image diagnosis is usable here. Never guesses — it actually
    attempts the (cached) model load."""
    from backend.tools.leaf_diagnosis import _MODEL_ID, _classifier, _load_error

    ready = _classifier() is not None
    return {"available": ready, "model_id": _MODEL_ID, "detail": None if ready else _load_error}


@router.post("/api/diagnose/image")
async def diagnose_image(file: UploadFile = File(...)) -> dict:
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail=f"expected an image, got {file.content_type!r}")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(payload) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"image larger than {_MAX_BYTES // (1024 * 1024)} MB")

    result = diagnose_leaf(payload)
    if result.get("error") == "model_unavailable":
        # 503, not 500: the request was fine, this deployment just cannot serve
        # it. The UI shows the Bangla message instead of a generic failure.
        raise HTTPException(status_code=503, detail=result.get("message_bn"))
    return result
