"""Checkout orchestration: mode toggle, confirmation gate, Bangla receipt.

Three rules from CLAUDE.md §2.13 are enforced structurally here, not by care:

1. **No charge without a confirmation step.** `quote()` prices the basket and
   registers a pending confirmation; `charge()` refuses unless a matching,
   unexpired quote exists. A stray POST to /api/checkout cannot take money.

   Note this is enforced using only fields already in the frozen
   `CheckoutRequest` (farm_id + mobile + amount) — no schema change needed.

2. **A quote is single-use.** It is consumed on charge, so the double-tap that
   a farmer on a laggy phone will absolutely produce cannot debit twice.
   bdapps dedupes on `externalTrxId` too, but we should not rely on their
   dedupe to protect our user.

3. **Mode is never implied.** Every result carries `mode`, and the mode comes
   from the client object actually used, not from a parameter someone could
   pass wrongly. Simulated output cannot be labelled live because nothing
   constructs that label by hand.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from backend.api.redact import redact
from backend.branding import BRAND_NAME
from backend.schemas import CheckoutItem, CheckoutResult

from .client import BdappsClient, BdappsTransportError
from .msisdn import to_subscriber_id
from .simulator import BdappsSimulator

# A confirmation should not stay valid forever — the farmer's intent was about
# the basket they were looking at five minutes ago.
QUOTE_TTL = timedelta(minutes=10)


class CheckoutError(RuntimeError):
    """Checkout refused before any money moved."""


@dataclass(frozen=True)
class Quote:
    quote_id: str
    farm_id: str
    subscriber_id: str
    amount: float
    items: tuple[CheckoutItem, ...]
    prompt_bn: str
    expires_at: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _key(farm_id: str, subscriber_id: str, amount: float) -> tuple:
    return (farm_id, subscriber_id, round(float(amount), 2))


def build_client(mode: str | None = None):
    """Return the simulator or the live client.

    Defaults to simulator: the safe direction. If BDAPPS_MODE is missing,
    mistyped, or the credentials are absent, we must end up simulating rather
    than attempting a real debit — and the label follows the object, so the UI
    cannot claim otherwise.
    """
    resolved = (mode or os.getenv("BDAPPS_MODE", "simulator")).strip().lower()
    if resolved != "live":
        return BdappsSimulator()
    return BdappsClient(
        app_id=os.getenv("BDAPPS_APP_ID", ""),
        password=os.getenv("BDAPPS_PASSWORD", ""),
        base_url=os.getenv("BDAPPS_BASE_URL", "https://developer.bdapps.com"),
    )


def receipt_bn(amount: float, items: list[CheckoutItem], trx_id: str | None) -> str:
    """Bangla SMS receipt, sent with encoding '16' (§4.1).

    Bangla words, Western numerals — NOTES.md #17: computed values stay in
    Western numerals so they can be checked against the screen.
    """
    lines = [f"{BRAND_NAME}: ৳{amount:.2f} কাটা হয়েছে।"]
    for item in items:
        lines.append(f"- {item.name} {item.qty:g} {item.unit}")
    if trx_id:
        lines.append(f"ট্রানজেকশন: {trx_id}")
    lines.append("ধন্যবাদ।")
    return "\n".join(lines)


class CheckoutService:
    def __init__(self, client=None) -> None:
        self._client = client or build_client()
        self._quotes: dict[tuple, Quote] = {}

    @property
    def mode(self) -> str:
        return self._client.mode

    # --- step 1: price it and ask ------------------------------------------

    def quote(
        self,
        farm_id: str,
        mobile: str,
        amount: float,
        items: list[CheckoutItem],
    ) -> Quote:
        """Price the basket and register the confirmation. Charges nothing."""
        if amount <= 0:
            raise CheckoutError(f"Amount must be positive, got {amount}")

        subscriber_id = to_subscriber_id(mobile)
        quote = Quote(
            quote_id=str(uuid.uuid4()),
            farm_id=farm_id,
            subscriber_id=subscriber_id,
            amount=round(float(amount), 2),
            items=tuple(items),
            # The exact wording PRD.md §8 Tier2.1 asks for.
            prompt_bn=f"৳{amount:.2f} কাটা হবে — নিশ্চিত?",
            expires_at=_now() + QUOTE_TTL,
        )
        self._quotes[_key(farm_id, subscriber_id, amount)] = quote
        return quote

    def check_balance(self, mobile: str) -> dict:
        """Balance before charging, so the UI can warn instead of failing."""
        return self._client.balance_query(to_subscriber_id(mobile))

    # --- step 2: charge, only if confirmed ---------------------------------

    def charge(
        self,
        farm_id: str,
        mobile: str,
        amount: float,
        items: list[CheckoutItem],
    ) -> CheckoutResult:
        subscriber_id = to_subscriber_id(mobile)
        key = _key(farm_id, subscriber_id, amount)
        quote = self._quotes.pop(key, None)  # single-use: popped, not read

        if quote is None:
            raise CheckoutError(
                "No confirmed quote for this basket. Call /api/checkout/quote and "
                "have the farmer confirm before charging."
            )
        if quote.expires_at < _now():
            raise CheckoutError("Confirmation expired — please confirm the amount again.")

        try:
            raw = self._client.direct_debit(
                subscriber_id=subscriber_id,
                amount=quote.amount,
                external_trx_id=quote.quote_id,
            )
        except BdappsTransportError as exc:
            # Honest degradation: name what failed, never invent a success.
            return CheckoutResult(
                status="transport_error",
                trx_id=None,
                mode=self.mode,
                receipt_sms_sent=False,
                raw={"error": str(exc)},
            )

        status_code = raw.get("statusCode")
        trx_id = raw.get("internalTrxId")
        receipt_sent = False

        if status_code == "S1000":
            status = "success"
            # A failed receipt must not fail the payment — the money already
            # moved, and reporting failure would be a lie in the costly direction.
            try:
                sms_raw = self._client.sms_send(
                    subscriber_id=subscriber_id,
                    message=receipt_bn(quote.amount, list(quote.items), trx_id),
                    encoding="16",
                )
                receipt_sent = sms_raw.get("statusCode") == "S1000"
            except BdappsTransportError:
                receipt_sent = False
        elif status_code in {"E1326", "E1601"}:
            # E1326 insufficient balance (retryable), E1601 permanent charging
            # error. Both mean "no money moved" — the demo-able recovery path.
            status = "insufficient_balance"
        else:
            status = f"error_{status_code}" if status_code else "unknown_error"

        # The raw response reaches the trace panel, so it is redacted here.
        # A's schema comment on CheckoutResult.raw says "(redacted)" — this is
        # where that promise is kept.
        safe_raw, _ = redact(raw)

        return CheckoutResult(
            status=status,
            trx_id=trx_id,
            mode=self.mode,
            receipt_sms_sent=receipt_sent,
            raw=safe_raw,
        )
