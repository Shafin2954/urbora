"""Live bdapps HTTP client.

Same method names and return shapes as BdappsSimulator, so the two are
interchangeable and the mode toggle is a one-line swap (NOTES.md #4 wants that
toggle rehearsed, not improvised on stage).

Auth rides in the request body — `applicationId` + `password` on every call,
no headers, no OAuth (§0). That is exactly why the trace redactor exists: these
bodies are shown to judges.

This path is DORMANT unless BDAPPS_MODE=live and credentials are present. It is
written now so that if the portal unblocks at H15–H18 it is a config change,
not a build.
"""

from __future__ import annotations

import json

import httpx

BASE_URL = "https://developer.bdapps.com"
TIMEOUT_SECONDS = 15.0


class BdappsTransportError(RuntimeError):
    """A call that never produced a usable bdapps response."""


class BdappsClient:
    """Live client. Mirrors BdappsSimulator's interface exactly."""

    mode = "live"

    def __init__(
        self,
        app_id: str,
        password: str,
        base_url: str = BASE_URL,
        timeout: float = TIMEOUT_SECONDS,
    ) -> None:
        if not app_id or not password:
            # Refusing to construct beats discovering it mid-charge.
            raise ValueError(
                "Live bdapps client needs BDAPPS_APP_ID and BDAPPS_PASSWORD. "
                "Set BDAPPS_MODE=simulator to run without credentials."
            )
        self._app_id = app_id
        self._password = password
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _post(self, path: str, body: dict) -> dict:
        payload = {
            "applicationId": self._app_id,
            "password": self._password,
            **body,
        }
        try:
            response = httpx.post(
                f"{self._base_url}{path}",
                json=payload,
                timeout=self._timeout,
                headers={"Content-Type": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise BdappsTransportError(f"bdapps {path} unreachable: {exc}") from exc

        text = response.text or ""

        # Gotcha #9: on errors bdapps (or a proxy in front of it) returns an
        # HTML page. Feeding that to json.loads produces a JSONDecodeError that
        # reads like a bug in our code, at the exact moment we most need to
        # know it was theirs. Detect it and say so.
        stripped = text.lstrip().lower()
        if stripped.startswith("<html") or stripped.startswith("<!doctype"):
            raise BdappsTransportError(
                f"bdapps {path} returned HTML, not JSON (HTTP {response.status_code}) — "
                "usually the IP is not whitelisted or the portal is down. "
                "Switch to simulator mode."
            )

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise BdappsTransportError(
                f"bdapps {path} returned unparseable body (HTTP {response.status_code}): "
                f"{text[:200]!r}"
            ) from exc

        if not isinstance(parsed, dict):
            raise BdappsTransportError(f"bdapps {path} returned {type(parsed).__name__}, expected object")
        return parsed

    # --- same surface as the simulator --------------------------------------

    def balance_query(self, subscriber_id: str) -> dict:
        return self._post(
            "/caas/balance/query",
            {
                "subscriberId": subscriber_id,
                "paymentInstrumentName": "Mobile Account",
                "currency": "BDT",
            },
        )

    def list_payment_instruments(self, subscriber_id: str) -> dict:
        return self._post("/caas/list/pi", {"subscriberId": subscriber_id, "type": "all"})

    def direct_debit(self, subscriber_id: str, amount: float, external_trx_id: str) -> dict:
        return self._post(
            "/caas/direct/debit",
            {
                "externalTrxId": external_trx_id,
                # Gotcha #7: amount is a STRING, 2dp, BDT only.
                "amount": f"{amount:.2f}",
                "subscriberId": subscriber_id,
                "paymentInstrumentName": "Mobile Account",
                "currency": "BDT",
            },
        )

    def sms_send(self, subscriber_id: str, message: str, encoding: str = "16") -> dict:
        return self._post(
            "/sms/send",
            {
                "message": message,
                "destinationAddresses": [subscriber_id],
                "version": "1.0",
                "deliveryStatusRequest": "0",
                # '16' = Bengali (§4.1). A Bangla receipt sent as encoding '0'
                # arrives as question marks on the farmer's handset.
                "encoding": encoding,
            },
        )
