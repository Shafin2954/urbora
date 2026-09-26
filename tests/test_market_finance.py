"""Marketplace money (CLAUDE.md rule 12): totals add up, who pays what."""

from decimal import Decimal

import pytest

from backend.finance import market


def test_farmer_total_does_not_move_with_the_commission_rate():
    items = [{"product_id": "p1", "name": "ইউরিয়া", "packs": 2, "price_per_pack": 1350},
             {"product_id": "p2", "name": "টিএসপি", "packs": 1, "price_per_pack": 1350.005}]
    low = market.order_totals(items, pct=Decimal("2"))
    high = market.order_totals(items, pct=Decimal("10"))
    assert low.subtotal == high.subtotal == Decimal("4050.01")
    assert high.commission == Decimal("405.00") and high.dealer_payout == Decimal("3645.01")
    assert low.commission + low.dealer_payout == low.subtotal


def test_line_totals_sum_exactly_to_the_subtotal():
    items = [{"product_id": str(i), "name": "x", "packs": 3, "price_per_pack": 33.333} for i in range(7)]
    t = market.order_totals(items, pct=Decimal("5"))
    assert sum(l.line_total for l in t.lines) == t.subtotal


@pytest.mark.parametrize("packs", [0, -1, 1.5])
def test_packs_must_be_whole_and_positive(packs):
    with pytest.raises(ValueError):
        market.order_totals([{"product_id": "p", "name": "x", "packs": packs, "price_per_pack": 10}])


def test_empty_order_is_refused():
    with pytest.raises(ValueError):
        market.order_totals([])


def test_commission_rate_comes_from_env_and_is_bounded(monkeypatch):
    monkeypatch.setenv("MARKET_COMMISSION_PCT", "7.5")
    assert market.commission_pct() == Decimal("7.5")
    monkeypatch.setenv("MARKET_COMMISSION_PCT", "80")
    with pytest.raises(ValueError):
        market.commission_pct()


@pytest.mark.parametrize("qty,size,packs", [(100, 50, 2), (101, 50, 3), (0.25, 0.1, 3), (50, 50, 1)])
def test_packs_needed_rounds_up(qty, size, packs):
    assert market.packs_needed(qty, size) == packs


def test_cost_for_quantity():
    out = market.cost_for_quantity(137.5, 50, 1350)
    assert out["packs"] == 3 and out["total_bdt"] == 4050.0


def test_unit_price_compares_pack_sizes():
    assert market.unit_price(1350, 50) == 27.0
    assert market.unit_price(85, 0.1) == 850.0


def test_produce_fee_is_paid_by_the_buyer():
    d = market.deal_totals(500, 22.5, pct=Decimal("2"))
    assert d["farmer_receives"] == 11250.0
    assert d["platform_fee"] == 225.0 and d["buyer_pays"] == 11475.0
