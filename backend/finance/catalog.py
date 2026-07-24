"""Reads `data/prices.md` into finance-engine inputs.

This is the seam between hand-curated, cited prices and the pure arithmetic in
`engine.py`. Everything money-shaped enters the system here, which is what makes
"no invented data" (CLAUDE.md §2.2) checkable rather than aspirational: if a
number is not in a cited table row, there is no code path that produces it.

The design goal is that **filling in a markdown row is the only action needed**
to switch on the finance tool, the Finance tab, and the crop scorer's Profit
component. No code change, no redeploy of logic — the yearbook extraction lands
and the feature lights up.

Two refusals are deliberate and worth defending:

1. **Retail is never revenue.** The retail table is parsed (the UI shows it as
   market context) but `projection_inputs` cannot reach it. Dhaka retail coarse
   rice is ~55 BDT/kg; the farmer sells *paddy*, unmilled. Wiring retail into
   revenue would roughly double every profit figure, in the direction that
   flatters us.

2. **Partial price data does not produce a partial ranking.** `scorer_finance`
   returns data for all requested crops or none. PRD §6 normalizes the Profit
   component min-max *within the candidate set*, so supplying three of five
   crops would rank the other two down for lacking a citation rather than for
   being worse crops. That is a data gap masquerading as an agronomic judgment.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from backend.schemas import Confidence, Provenance

from .engine import CostLine, min_cost_per_ha, project

# Canonical crop keys (backend/tools/cropdb.py CANON_TO_KEY). A row naming
# anything else is ignored rather than guessed at.
CROPS = frozenset({"boro_rice", "aman_rice", "potato", "mustard", "lentil"})

PRICES_MD = Path(__file__).resolve().parents[2] / "data" / "prices.md"


def _prices_path() -> Path:
    """Where prices come from. `AGRISENSE_PRICES_MD` overrides the default.

    The override exists so a curated file can be swapped in — or exercised —
    without editing the committed one. It is a path, not a set of values: there
    is still no way to get a price into the system that is not a cited row in a
    markdown table.
    """
    override = os.getenv("AGRISENSE_PRICES_MD", "").strip()
    return Path(override) if override else PRICES_MD

_SECTION_FARM_GATE = "1. Selling price"
_SECTION_INPUT_COSTS = "2. Input costs"
_SECTION_RETAIL = "3. Retail market context"


class PriceDataUnavailable(Exception):
    """Raised instead of returning a number nobody can cite."""

    def __init__(self, crop: str, missing: list[str]) -> None:
        self.crop = crop
        self.missing = missing
        super().__init__(f"{crop}: no cited data for {', '.join(missing)}")


@dataclass(frozen=True)
class PriceRow:
    crop: str
    price_bdt_per_kg: float
    basis: str
    source_id: str
    source_title: str
    locator: str
    date: str
    confidence: Confidence


@dataclass(frozen=True)
class RetailRow:
    """Market context only. Structurally cannot enter a projection."""

    commodity: str
    related_crop: str
    price_min_bdt_per_kg: float
    price_max_bdt_per_kg: float
    note: str


# --- markdown table parsing --------------------------------------------------


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_divider(cells: list[str]) -> bool:
    return all(set(cell) <= set("-: ") and cell for cell in cells)


def _tables_under(text: str, heading: str) -> list[dict[str, str]]:
    """Every table row under `## <heading>`, as header-keyed dicts.

    Matching columns by header name rather than position means the curator can
    add a column or reorder them without silently shifting every value one to
    the left — which is exactly the kind of error that would go unnoticed until
    a judge asked why urea costs 2 BDT.
    """
    body = None
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        if block.startswith(heading):
            body = block
            break
    if body is None:
        return []

    # HTML comments hold the "example row, do not uncomment" documentation.
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)

    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            header = None  # a non-table line ends the current table
            continue
        cells = _split_row(line)
        if header is None:
            header = cells
            continue
        if _is_divider(cells):
            continue
        if len(cells) != len(header):
            continue  # malformed row: skip rather than misalign
        rows.append(dict(zip(header, cells)))
    return rows


def _number(raw: str | None) -> float | None:
    """A blank cell means absent, never zero — zero is a claim."""
    if raw is None or not raw.strip():
        return None
    try:
        return float(raw.strip())
    except ValueError:
        return None


def _confidence(raw: str) -> Confidence:
    value = (raw or "").strip().lower()
    # Market prices move (PRD §7), so anything unlabelled lands on the cautious
    # side rather than claiming certainty we did not write down.
    return value if value in {"high", "medium", "low"} else "medium"  # type: ignore[return-value]


# --- the catalog -------------------------------------------------------------


class PriceCatalog:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else _prices_path()
        text = self.path.read_text(encoding="utf-8") if self.path.exists() else ""
        self._prices = self._read_prices(text)
        self._costs = self._read_costs(text)
        self.retail = self._read_retail(text)

    # -- parsing --

    def _read_prices(self, text: str) -> dict[str, PriceRow]:
        out: dict[str, PriceRow] = {}
        for row in _tables_under(text, _SECTION_FARM_GATE):
            crop = row.get("crop", "").strip()
            price = _number(row.get("price_bdt_per_kg"))
            if crop not in CROPS or price is None or price <= 0:
                continue
            out[crop] = PriceRow(
                crop=crop,
                price_bdt_per_kg=price,
                basis=row.get("basis", "").strip(),
                source_id=row.get("source_id", "").strip() or "prices.md",
                source_title=row.get("source_title", "").strip() or "data/prices.md",
                locator=row.get("locator", "").strip(),
                date=row.get("date", "").strip(),
                confidence=_confidence(row.get("confidence", "")),
            )
        return out

    def _read_costs(self, text: str) -> dict[str, list[CostLine]]:
        out: dict[str, list[CostLine]] = {}
        for row in _tables_under(text, _SECTION_INPUT_COSTS):
            crop = row.get("crop", "").strip()
            qty = _number(row.get("qty_per_ha"))
            unit_cost = _number(row.get("unit_cost_bdt"))
            item = row.get("item", "").strip()
            if crop not in CROPS or not item or qty is None or unit_cost is None:
                continue
            out.setdefault(crop, []).append(
                CostLine(
                    name=item,
                    qty_per_ha=qty,
                    unit=row.get("unit", "").strip() or "unit",
                    unit_cost_bdt=unit_cost,
                    provenance=Provenance(
                        value=unit_cost,
                        unit=f"BDT/{row.get('unit', 'unit').strip()}",
                        source_type="static_table",
                        source_id=row.get("source_id", "").strip() or "prices.md",
                        source_title=row.get("source_title", "").strip()
                        or "data/prices.md",
                        locator=row.get("locator", "").strip(),
                        retrieved_at=row.get("date", "").strip() or _now(),
                        confidence=_confidence(row.get("confidence", "")),
                    ),
                )
            )
        return out

    def _read_retail(self, text: str) -> list[RetailRow]:
        out: list[RetailRow] = []
        for row in _tables_under(text, _SECTION_RETAIL):
            lo = _number(row.get("price_min_bdt_per_kg"))
            hi = _number(row.get("price_max_bdt_per_kg"))
            if lo is None or hi is None:
                continue
            out.append(
                RetailRow(
                    commodity=row.get("commodity", "").strip(),
                    related_crop=row.get("related_crop", "").strip(),
                    price_min_bdt_per_kg=lo,
                    price_max_bdt_per_kg=hi,
                    note=row.get("note", "").strip(),
                )
            )
        return out

    # -- queries --

    def price(self, crop: str) -> PriceRow | None:
        return self._prices.get(crop)

    def cost_lines(self, crop: str) -> list[CostLine]:
        return list(self._costs.get(crop, ()))

    def missing_for(self, crop: str) -> list[str]:
        """What this crop still needs before it can be costed. Empty = ready."""
        gaps = []
        if crop not in CROPS:
            return [f"unknown crop '{crop}'"]
        if not self._costs.get(crop):
            gaps.append("input costs")
        if crop not in self._prices:
            gaps.append("farm-gate selling price")
        return gaps

    def priced_crops(self) -> list[str]:
        return sorted(c for c in CROPS if not self.missing_for(c))

    def price_provenance(self, crop: str) -> Provenance:
        row = self._prices[crop]
        return Provenance(
            value=row.price_bdt_per_kg,
            unit="BDT/kg",
            source_type="static_table",
            source_id=row.source_id,
            source_title=row.source_title,
            locator=row.locator or None,
            retrieved_at=row.date or _now(),
            confidence=row.confidence,
        )

    # -- the two consumers --

    def projection(
        self,
        crop: str,
        area_ha: float,
        base_yield_kg_ha: float,
        band_kg_ha: float,
        yield_provenance: Provenance,
        extra_assumptions: list[Provenance] | None = None,
    ):
        """Full three-scenario projection, or `PriceDataUnavailable`.

        The yield comes from crop.db (the caller's job); the money comes from
        here. Splitting it that way keeps each number's origin obvious in the
        trace.
        """
        gaps = self.missing_for(crop)
        if gaps:
            raise PriceDataUnavailable(crop, gaps)
        return project(
            area_ha=area_ha,
            cost_lines=self.cost_lines(crop),
            base_yield_kg_ha=base_yield_kg_ha,
            band_kg_ha=band_kg_ha,
            price_per_kg=self._prices[crop].price_bdt_per_kg,
            yield_provenance=yield_provenance,
            price_provenance=self.price_provenance(crop),
            extra_assumptions=extra_assumptions,
        )

    def scorer_finance(
        self, crops: list[str], yields_kg_ha: dict[str, float]
    ) -> tuple[dict[str, dict] | None, str | None]:
        """Build the crop scorer's `finance` seam, or explain why not.

        Returns `(finance, None)` when every requested crop can be costed, else
        `(None, reason)`. All-or-nothing on purpose — see the module docstring.
        """
        ungettable = [c for c in crops if self.missing_for(c) or c not in yields_kg_ha]
        if ungettable:
            return None, (
                "profit comparison needs cited prices and costs for every candidate; "
                f"missing for: {', '.join(sorted(ungettable))}"
            )

        finance: dict[str, dict] = {}
        for crop in crops:
            lines = self.cost_lines(crop)
            cost_per_ha = min_cost_per_ha(lines)
            price = self._prices[crop].price_bdt_per_kg
            revenue_per_ha = yields_kg_ha[crop] * price
            finance[crop] = {
                "min_cost_per_ha": cost_per_ha,
                "net_profit_bdt_per_ha": round(revenue_per_ha - cost_per_ha, 2),
                "source_id": self._prices[crop].source_id,
                "source_title": self._prices[crop].source_title,
                "formula": (
                    f"({yields_kg_ha[crop]:g} kg/ha x {price:g} BDT/kg) - "
                    f"{cost_per_ha:g} BDT/ha input cost"
                ),
            }
        return finance, None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


_CACHED: PriceCatalog | None = None


def load_catalog(refresh: bool = False) -> PriceCatalog:
    """Process-wide catalog. `refresh=True` re-reads the file.

    Cached because it is read on every scorer call and the file is small and
    static during a run; refreshable because the whole point is that someone
    can fill in a row mid-event.
    """
    global _CACHED
    if _CACHED is None or refresh:
        _CACHED = PriceCatalog()
    return _CACHED
