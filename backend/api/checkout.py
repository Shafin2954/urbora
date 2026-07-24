"""Checkout routes (PLAN.md §2: POST /api/checkout -> CheckoutResult).

Two endpoints, because CLAUDE.md §2.13 requires a confirmation step before any
charge:

    POST /api/checkout/quote   prices the basket, charges nothing, returns the
                               Bangla confirmation prompt
    POST /api/checkout         charges — and refuses unless a matching quote
                               was confirmed first

Both take the frozen `CheckoutRequest` shape, so the confirmation gate needed
no schema change: the quote is keyed on farm_id + mobile + amount, all fields
that already exist.

The service is a module-level singleton because the pending-quote store lives
in memory. That is fine for a single-process demo and is the honest scope —
a multi-worker deployment would need the quotes in SQLite, which is a Tier-1
concern, not a Tier-0 one.
"""

from fastapi import APIRouter, HTTPException

from backend.payments import CheckoutError, CheckoutService, receipt_bn
from backend.payments.msisdn import InvalidMsisdnError, mask
from backend.schemas import CheckoutRequest, CheckoutResult

router = APIRouter()

_service = CheckoutService()


@router.get("/api/checkout/mode")
async def checkout_mode() -> dict:
    """What mode payments are in.

    The UI reads this to label the checkout. CLAUDE.md §2.13: the mode must be
    visible in the UI, and it comes from the client object actually in use —
    it is never something the frontend assumes.
    """
    return {"mode": _service.mode}


@router.post("/api/checkout/quote")
async def checkout_quote(payload: CheckoutRequest) -> dict:
    """Price the basket and register the confirmation. Charges nothing."""
    try:
        quote = _service.quote(
            farm_id=payload.farm_id,
            mobile=payload.mobile,
            amount=payload.amount,
            items=payload.items,
        )
    except InvalidMsisdnError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CheckoutError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Balance is best-effort: knowing in advance lets the UI warn instead of
    # letting the farmer confirm a charge that is going to bounce. If the
    # lookup fails we continue — it must not block the checkout.
    balance = None
    try:
        raw = _service.check_balance(payload.mobile)
        if raw.get("statusCode") == "S1000":
            balance = float(raw["chargeableBalance"])
    except Exception:
        balance = None

    return {
        "quote_id": quote.quote_id,
        "amount": quote.amount,
        "prompt_bn": quote.prompt_bn,
        "items": [item.model_dump() for item in quote.items],
        "mobile_masked": mask(payload.mobile),
        "balance_bdt": balance,
        "sufficient": None if balance is None else balance >= quote.amount,
        "mode": _service.mode,
        "expires_at": quote.expires_at.isoformat(timespec="seconds"),
    }


@router.post("/api/checkout")
async def checkout(payload: CheckoutRequest) -> dict:
    """Charge. Refuses with 409 unless the amount was confirmed via /quote.

    Returns every `CheckoutResult` field plus `receipt_bn` — additive, the same
    pattern as `redacted` on the trace events. The receipt is included because
    the screen must show the farmer *the text that was sent to their phone*,
    and building a second copy of that wording in JavaScript is how the SMS and
    the screen end up disagreeing about what was bought.

    It is null unless the charge succeeded. A receipt for a payment that did
    not happen is the one lie this module must never tell.
    """
    try:
        result: CheckoutResult = _service.charge(
            farm_id=payload.farm_id,
            mobile=payload.mobile,
            amount=payload.amount,
            items=payload.items,
        )
    except InvalidMsisdnError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CheckoutError as exc:
        # 409: the request is well-formed but the required confirmation is
        # missing or stale. Distinct from 400 so the UI can re-prompt.
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        **result.model_dump(),
        "receipt_bn": (
            receipt_bn(payload.amount, payload.items, result.trx_id)
            if result.status == "success"
            else None
        ),
    }
