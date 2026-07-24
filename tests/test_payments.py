"""bdapps payments tests (CLAUDE.md §2.12/§2.13 — 10 judged points).

What these guard:
  * the simulator returns the DOCUMENTED shapes, field for field
  * no charge is possible without a confirmation step
  * a double-tap cannot debit twice
  * simulated output is never labelled live
  * credentials never reach the trace
  * the E1326 insufficient-balance recovery path actually works

Run from the repo root:  .venv/Scripts/python -m pytest tests/ -q
"""

import pytest

from backend.payments import (
    BdappsSimulator,
    CheckoutError,
    CheckoutService,
    InvalidMsisdnError,
    build_client,
    mask,
    normalise,
    receipt_bn,
    to_subscriber_id,
)
from backend.payments.client import BdappsClient
from backend.schemas import CheckoutItem

MOBILE = "01812345678"
ITEMS = [
    CheckoutItem(name="ইউরিয়া", qty=10, unit="kg", unit_price_bdt=27.0),
    CheckoutItem(name="বীজ", qty=2, unit="kg", unit_price_bdt=50.0),
]


@pytest.fixture
def service():
    return CheckoutService(client=BdappsSimulator())


# --- msisdn normalisation (gotcha #4: E1325 on a bad address) ---------------


@pytest.mark.parametrize(
    "raw",
    [
        "01812345678",
        "+8801812345678",
        "8801812345678",
        "01812-345678",
        " 018 1234 5678 ",
        "8801812345678",
    ],
)
def test_all_the_ways_a_farmer_types_a_number(raw):
    assert to_subscriber_id(raw) == "tel:8801812345678"


@pytest.mark.parametrize("prefix", ["013", "014", "015", "016", "017", "018", "019"])
def test_all_operator_prefixes_accepted(prefix):
    """Rejecting a valid number is worse than letting bdapps decline it."""
    assert normalise(f"{prefix}12345678") == f"{prefix}12345678"


@pytest.mark.parametrize("bad", ["", "12345", "01212345678", "0181234567", "abcdefghijk", "০১৮১২৩৪৫৬৭৮"])
def test_invalid_numbers_raise_rather_than_being_fixed(bad):
    """Silently 'correcting' a number could charge a stranger."""
    with pytest.raises(InvalidMsisdnError):
        to_subscriber_id(bad)


def test_mask_shows_last_three_only():
    assert mask(MOBILE) == "***678"
    assert mask("nonsense") == "***"


# --- simulator shapes match the reference doc ------------------------------


def test_balance_query_shape(service):
    raw = BdappsSimulator().balance_query(to_subscriber_id(MOBILE))
    assert raw["statusCode"] == "S1000"
    assert set(raw) == {
        "statusCode",
        "chargeableBalance",
        "accountStatus",
        "accountType",
        "statusDetail",
    }
    # Gotcha #7: numeric-looking fields are STRINGS in bdapps JSON. Code
    # written against the twin must not break on the live API.
    assert isinstance(raw["chargeableBalance"], str)


def test_payment_instruments_shape():
    raw = BdappsSimulator().list_payment_instruments(to_subscriber_id(MOBILE))
    assert raw["statusCode"] == "S1000"
    assert raw["paymentInstrumentList"] == [{"name": "Mobile Account", "type": "sync"}]


def test_direct_debit_success_shape():
    raw = BdappsSimulator().direct_debit(to_subscriber_id(MOBILE), 5.0, "trx-1")
    assert raw["statusCode"] == "S1000"
    assert set(raw) == {
        "statusCode",
        "timeStamp",
        "externalTrxId",
        "internalTrxId",
        "statusDetail",
    }
    assert raw["externalTrxId"] == "trx-1"


def test_sms_send_shape():
    raw = BdappsSimulator().sms_send(to_subscriber_id(MOBILE), "পরীক্ষা", encoding="16")
    assert raw["statusCode"] == "S1000"
    assert raw["destinationResponses"][0]["address"] == "tel:8801812345678"
    assert raw["version"] == "1.0"


# --- the confirmation gate --------------------------------------------------


def test_charge_without_confirmation_is_refused(service):
    """CLAUDE.md §2.13: checkout ALWAYS has a confirmation step before charging."""
    with pytest.raises(CheckoutError, match="No confirmed quote"):
        service.charge(farm_id="f1", mobile=MOBILE, amount=50.0, items=ITEMS)


def test_quote_charges_nothing(service):
    before = service.check_balance(MOBILE)["chargeableBalance"]
    service.quote(farm_id="f1", mobile=MOBILE, amount=50.0, items=ITEMS)
    after = service.check_balance(MOBILE)["chargeableBalance"]
    assert before == after


def test_quote_prompt_is_the_bangla_confirmation(service):
    quote = service.quote(farm_id="f1", mobile=MOBILE, amount=50.0, items=ITEMS)
    assert quote.prompt_bn == "৳50.00 কাটা হবে — নিশ্চিত?"


def test_confirmed_charge_succeeds_and_debits(service):
    service.quote(farm_id="f1", mobile=MOBILE, amount=50.0, items=ITEMS)
    result = service.charge(farm_id="f1", mobile=MOBILE, amount=50.0, items=ITEMS)

    assert result.status == "success"
    assert result.trx_id
    assert result.mode == "simulator"
    assert result.receipt_sms_sent is True
    assert float(service.check_balance(MOBILE)["chargeableBalance"]) == 50.0


def test_double_tap_cannot_charge_twice(service):
    """A quote is single-use. The farmer's laggy phone must not cost them twice."""
    service.quote(farm_id="f1", mobile=MOBILE, amount=50.0, items=ITEMS)
    first = service.charge(farm_id="f1", mobile=MOBILE, amount=50.0, items=ITEMS)
    assert first.status == "success"

    with pytest.raises(CheckoutError):
        service.charge(farm_id="f1", mobile=MOBILE, amount=50.0, items=ITEMS)
    assert float(service.check_balance(MOBILE)["chargeableBalance"]) == 50.0


def test_confirming_one_amount_does_not_authorise_another(service):
    """Confirmation is for the basket the farmer actually looked at."""
    service.quote(farm_id="f1", mobile=MOBILE, amount=50.0, items=ITEMS)
    with pytest.raises(CheckoutError):
        service.charge(farm_id="f1", mobile=MOBILE, amount=500.0, items=ITEMS)


def test_expired_confirmation_is_refused(service):
    from datetime import datetime, timedelta, timezone

    quote = service.quote(farm_id="f1", mobile=MOBILE, amount=50.0, items=ITEMS)
    key = ("f1", to_subscriber_id(MOBILE), 50.0)
    service._quotes[key] = type(quote)(
        **{**quote.__dict__, "expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}
    )
    with pytest.raises(CheckoutError, match="expired"):
        service.charge(farm_id="f1", mobile=MOBILE, amount=50.0, items=ITEMS)


def test_zero_or_negative_amount_refused(service):
    for bad in (0, -10):
        with pytest.raises(CheckoutError):
            service.quote(farm_id="f1", mobile=MOBILE, amount=bad, items=ITEMS)


# --- E1326: the demo-able recovery -----------------------------------------


def test_insufficient_balance_path(service):
    """NOTES.md #4 / PRD.md §8 Tier2.1 — E1326 must be demonstrable."""
    service._client.state.set_balance(to_subscriber_id(MOBILE), 10.0)
    service.quote(farm_id="f1", mobile=MOBILE, amount=500.0, items=ITEMS)
    result = service.charge(farm_id="f1", mobile=MOBILE, amount=500.0, items=ITEMS)

    assert result.status == "insufficient_balance"
    assert result.trx_id is None
    assert result.receipt_sms_sent is False
    assert result.raw["statusCode"] == "E1326"
    # Crucially: no money moved.
    assert float(service.check_balance(MOBILE)["chargeableBalance"]) == 10.0


def test_failed_charge_sends_no_receipt(service):
    service._client.state.set_balance(to_subscriber_id(MOBILE), 1.0)
    service.quote(farm_id="f1", mobile=MOBILE, amount=99.0, items=ITEMS)
    result = service.charge(farm_id="f1", mobile=MOBILE, amount=99.0, items=ITEMS)
    assert result.receipt_sms_sent is False


# --- mode honesty (CLAUDE.md §2.13) ----------------------------------------


def test_simulator_never_labels_itself_live(service):
    service.quote(farm_id="f1", mobile=MOBILE, amount=5.0, items=ITEMS)
    result = service.charge(farm_id="f1", mobile=MOBILE, amount=5.0, items=ITEMS)
    assert result.mode == "simulator"
    assert service.mode == "simulator"


def test_mode_defaults_to_simulator_when_unset(monkeypatch):
    """The safe direction: a missing/typo'd mode must never attempt a real debit."""
    monkeypatch.delenv("BDAPPS_MODE", raising=False)
    assert build_client().mode == "simulator"
    monkeypatch.setenv("BDAPPS_MODE", "SiMuLaToR")
    assert build_client().mode == "simulator"
    monkeypatch.setenv("BDAPPS_MODE", "nonsense")
    assert build_client().mode == "simulator"


def test_live_mode_without_credentials_refuses_to_construct(monkeypatch):
    monkeypatch.setenv("BDAPPS_MODE", "live")
    monkeypatch.setenv("BDAPPS_APP_ID", "")
    monkeypatch.setenv("BDAPPS_PASSWORD", "")
    with pytest.raises(ValueError, match="BDAPPS_APP_ID"):
        build_client()


def test_live_client_reports_live_mode():
    assert BdappsClient(app_id="APP_1", password="x" * 32).mode == "live"


# --- receipt ----------------------------------------------------------------


def test_receipt_is_bangla_with_western_numerals():
    text = receipt_bn(137.0, ITEMS, "913080108430074")
    assert "কাটা হয়েছে" in text          # Bangla words
    assert "137.00" in text               # Western numerals (NOTES.md #17)
    assert "913080108430074" in text
    assert "ইউরিয়া" in text


# --- the trace must never carry credentials --------------------------------


def test_checkout_raw_is_redacted_before_it_reaches_the_ui():
    """CheckoutResult.raw goes to the trace panel; A's schema promises redaction."""

    class LeakyClient:
        mode = "simulator"

        def direct_debit(self, subscriber_id, amount, external_trx_id):
            # A response echoing the request, credentials and all.
            return {
                "statusCode": "S1000",
                "internalTrxId": "913080108430074",
                "applicationId": "APP_000123",
                "password": "9f8e7d6c5b4a39281706f5e4d3c2b1a0",
                "subscriberId": subscriber_id,
            }

        def sms_send(self, subscriber_id, message, encoding="16"):
            return {"statusCode": "S1000"}

        def balance_query(self, subscriber_id):
            return {"statusCode": "S1000", "chargeableBalance": "100"}

    service = CheckoutService(client=LeakyClient())
    service.quote(farm_id="f1", mobile=MOBILE, amount=5.0, items=ITEMS)
    result = service.charge(farm_id="f1", mobile=MOBILE, amount=5.0, items=ITEMS)

    assert result.raw["password"] == "***"
    assert result.raw["applicationId"] == "***"
    assert result.raw["subscriberId"] == "***678"
    assert "9f8e7d6c5b4a39281706f5e4d3c2b1a0" not in repr(result)
    assert "8801812345678" not in repr(result)
    # The judge-relevant fields survive.
    assert result.raw["statusCode"] == "S1000"
    assert result.trx_id == "913080108430074"
