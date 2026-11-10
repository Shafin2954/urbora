"""bdapps simulator twin.

docs/NOTES.md #4: the simulator is PRIMARY, not a fallback. The portal needs public
receiving URLs we do not have, and the venue IP must be whitelisted (`E1312`),
so the demo cannot depend on the live path existing. What it *can* depend on is
a twin that returns the documented shapes exactly.

CLAUDE.md §2.13 — simulator honesty:
  * shapes match docs/channels/BDAPPS-API-REFERENCE.md field for field
  * every result is labelled `mode: "simulator"` in code, UI and README
  * simulated output is NEVER presented as live

Every response below is copied from the reference doc, not invented:
  balance  §6.1   debit   §6.3   sms  §4.1   error codes  §8

The demo-able failure is `E1326` (insufficient balance, retryable) — named in
docs/product/PRD.md §8 Tier2.1 and docs/NOTES.md #4, and confirmed in the §8 code table.

DOC INCONSISTENCY, flagged rather than silently resolved: the inline note under
§6.3 says "E1602 insufficient balance (retry-able)" and mentions `E1328`, but
the authoritative §8 table says `E1326` = insufficient balance and `E1602` =
message delivery failed; `E1328` is absent entirely. This twin follows the §8
table, because that is the appendix the codes are specified in and it agrees
with the PRD.
"""

from __future__ import annotations

import itertools
from datetime import datetime, timedelta, timezone

# Bangladesh is UTC+6; bdapps timestamps carry an offset (§6.3 shows +05:30 in
# their own example). Ours are honest about being simulated but correctly
# shaped, so any client-side parsing we write works against the live path too.
_BD_TZ = timezone(timedelta(hours=6))

_trx_counter = itertools.count(913080108430074)


def _timestamp() -> str:
    return datetime.now(_BD_TZ).isoformat(timespec="milliseconds")


def _sms_timestamp() -> str:
    # §4.1 delivery responses use a compact form, not ISO.
    return datetime.now(_BD_TZ).strftime("%Y%m%d%H%M%S")


class SimulatorState:
    """Mutable balances so the demo can actually run out of money.

    A twin that always succeeds cannot demonstrate the recovery moment the
    insufficient-balance path exists for, so balances really are debited.
    """

    DEFAULT_BALANCE_BDT = 100.0

    def __init__(self) -> None:
        self._balances: dict[str, float] = {}

    def balance_of(self, subscriber_id: str) -> float:
        return self._balances.setdefault(subscriber_id, self.DEFAULT_BALANCE_BDT)

    def set_balance(self, subscriber_id: str, amount: float) -> None:
        """Used by the demo drill to force the E1326 path on cue."""
        self._balances[subscriber_id] = amount

    def debit(self, subscriber_id: str, amount: float) -> None:
        self._balances[subscriber_id] = self.balance_of(subscriber_id) - amount

    def reset(self) -> None:
        self._balances.clear()


class BdappsSimulator:
    """Drop-in twin of the live client. Same method names, same return shapes."""

    mode = "simulator"

    def __init__(self, state: SimulatorState | None = None) -> None:
        self.state = state or SimulatorState()

    # --- §6.1 balance query -------------------------------------------------

    def balance_query(self, subscriber_id: str) -> dict:
        balance = self.state.balance_of(subscriber_id)
        return {
            "statusCode": "S1000",
            # bdapps returns numeric-looking fields as STRINGS (gotcha #7).
            # Matching that matters: code written against the twin must not
            # break the first time it meets the live API.
            "chargeableBalance": f"{balance:.0f}",
            "accountStatus": "0",
            "accountType": "PREPAID",
            "statusDetail": "Successful",
        }

    # --- §6.2 payment instruments ------------------------------------------

    def list_payment_instruments(self, subscriber_id: str) -> dict:
        return {
            "statusCode": "S1000",
            "paymentInstrumentList": [{"name": "Mobile Account", "type": "sync"}],
            "statusDetail": "Success",
        }

    # --- §6.3 direct debit --------------------------------------------------

    def direct_debit(
        self,
        subscriber_id: str,
        amount: float,
        external_trx_id: str,
    ) -> dict:
        balance = self.state.balance_of(subscriber_id)

        if amount > balance:
            # §8: E1326 insufficient balance, retryable. No balance is moved.
            return {
                "statusCode": "E1326",
                "timeStamp": _timestamp(),
                "externalTrxId": external_trx_id,
                "statusDetail": "Insufficient balance",
            }

        self.state.debit(subscriber_id, amount)
        return {
            "statusCode": "S1000",
            "timeStamp": _timestamp(),
            "externalTrxId": external_trx_id,
            "internalTrxId": str(next(_trx_counter)),
            "statusDetail": "Successful",
        }

    # --- §4.1 SMS send ------------------------------------------------------

    def sms_send(self, subscriber_id: str, message: str, encoding: str = "16") -> dict:
        """encoding '16' = Bengali (§4.1). The receipt is a Bangla SMS."""
        request_id = f"1013073111440{next(_trx_counter) % 100000:05d}"
        return {
            "statusCode": "S1000",
            "requestId": request_id,
            "statusDetail": "Request was successfully processed",
            "destinationResponses": [
                {
                    "statusCode": "S1000",
                    "timeStamp": _sms_timestamp(),
                    "address": subscriber_id,
                    "statusDetail": "Successful",
                    "messageId": request_id,
                }
            ],
            "version": "1.0",
        }
