"""Marketplace money: order totals, commission, packs needed, produce-deal fee.

The only place marketplace arithmetic happens (CLAUDE.md rule 1), in Decimal,
same discipline as engine.py: round each line, then sum the rounded lines, so
the numbers on the farmer's screen and SMS always add up exactly.

Who pays what (business model in the concept note, LOG.md):
- Input marketplace: the **dealer** pays the commission out of the sale. The
  farmer pays the listed price and nothing more — so a farmer's total never
  moves when the commission rate changes.
- Produce marketplace: the **buyer** pays the platform fee on top of the agreed
  price. The farmer receives the full agreed amount.

Rates are pilot parameters, not data: `MARKET_COMMISSION_PCT` and
`PRODUCE_FEE_PCT` in the environment, defaults below.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

TAKA = Decimal("0.01")
DEFAULT_COMMISSION_PCT = Decimal("5")
DEFAULT_PRODUCE_FEE_PCT = Decimal("2")


def _dec(value) -> Decimal:
    if isinstance(value, float):
        return Decimal(repr(value))
    return Decimal(str(value))


def _money(value: Decimal) -> Decimal:
    return value.quantize(TAKA, rounding=ROUND_HALF_UP)


def _pct(env: str, default: Decimal) -> Decimal:
    raw = os.environ.get(env, "").strip()
    try:
        pct = Decimal(raw) if raw else default
    except ArithmeticError:
        pct = default
    if not Decimal("0") <= pct <= Decimal("50"):
        raise ValueError(f"{env} must be between 0 and 50, got {pct}")
    return pct


def commission_pct() -> Decimal:
    return _pct("MARKET_COMMISSION_PCT", DEFAULT_COMMISSION_PCT)


def produce_fee_pct() -> Decimal:
    return _pct("PRODUCE_FEE_PCT", DEFAULT_PRODUCE_FEE_PCT)


@dataclass(frozen=True)
class OrderLine:
    product_id: str
    name: str
    packs: int
    price_per_pack: Decimal
    line_total: Decimal


@dataclass(frozen=True)
class OrderTotals:
    lines: tuple[OrderLine, ...]
    subtotal: Decimal          # what the farmer pays
    commission_pct: Decimal
    commission: Decimal        # what the platform earns, paid by the dealer
    dealer_payout: Decimal     # subtotal - commission

    def as_dict(self) -> dict:
        return {
            "lines": [{"product_id": l.product_id, "name": l.name, "packs": l.packs,
                       "price_per_pack": float(l.price_per_pack), "line_total": float(l.line_total)}
                      for l in self.lines],
            "farmer_pays": float(self.subtotal),
            "commission_pct": float(self.commission_pct),
            "commission": float(self.commission),
            "dealer_payout": float(self.dealer_payout),
            "formula": "farmer_pays = Σ packs × price_per_pack; commission = farmer_pays × pct / 100 "
                       "(paid by dealer); dealer_payout = farmer_pays − commission",
        }


def order_totals(items: list[dict], pct: Decimal | None = None) -> OrderTotals:
    """items: [{product_id, name, packs, price_per_pack}]. packs must be ≥1."""
    if not items:
        raise ValueError("an order needs at least one item")
    rate = commission_pct() if pct is None else _dec(pct)
    lines = []
    for item in items:
        packs = int(item["packs"])
        if packs < 1 or packs != item["packs"]:
            raise ValueError(f"packs must be a whole number ≥1, got {item['packs']!r}")
        price = _money(_dec(item["price_per_pack"]))
        if price <= 0:
            raise ValueError("price_per_pack must be positive")
        lines.append(OrderLine(item["product_id"], item["name"], packs, price, _money(price * packs)))
    subtotal = sum((l.line_total for l in lines), Decimal("0"))
    commission = _money(subtotal * rate / 100)
    return OrderTotals(tuple(lines), subtotal, rate, commission, subtotal - commission)


def packs_needed(qty: float, pack_size: float) -> int:
    """Whole packs to cover `qty` (same unit as pack_size), rounding up."""
    q, size = _dec(qty), _dec(pack_size)
    if q <= 0 or size <= 0:
        raise ValueError("quantity and pack size must be positive")
    return int((q / size).to_integral_value(rounding=ROUND_CEILING))


def cost_for_quantity(qty: float, pack_size: float, price_per_pack: float) -> dict:
    """Cost of covering `qty` from one listing, in whole packs."""
    packs = packs_needed(qty, pack_size)
    total = _money(_dec(price_per_pack) * packs)
    return {"packs": packs, "total_bdt": float(total),
            "formula": f"ceil({float(qty):g} / {float(pack_size):g}) = {packs} packs × ৳{float(price_per_pack):g} = ৳{total}"}


def unit_price(price_per_pack: float, pack_size: float) -> float:
    """Price per kg / litre, for comparing listings of different pack sizes."""
    return float(_money(_dec(price_per_pack) / _dec(pack_size)))


def deal_totals(qty_kg: float, price_per_kg: float, pct: Decimal | None = None) -> dict:
    """Produce deal: farmer receives qty × price in full; buyer pays that plus the fee."""
    q, p = _dec(qty_kg), _dec(price_per_kg)
    if q <= 0 or p <= 0:
        raise ValueError("quantity and price must be positive")
    rate = produce_fee_pct() if pct is None else _dec(pct)
    farmer_receives = _money(q * p)
    fee = _money(farmer_receives * rate / 100)
    return {
        "farmer_receives": float(farmer_receives),
        "fee_pct": float(rate),
        "platform_fee": float(fee),
        "buyer_pays": float(farmer_receives + fee),
        "formula": "farmer_receives = qty_kg × price_per_kg; platform_fee = farmer_receives × pct / 100 "
                   "(paid by buyer); buyer_pays = farmer_receives + platform_fee",
    }
