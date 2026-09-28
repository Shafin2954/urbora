"""Marketplace routes (backend/market/*).

Farmers act by farm_id (the web app's own farm id, or a phone's salted-hash
id). Dealers and buyers act with the token they receive when they register
(`X-Dealer-Token` / `X-Buyer-Token`) — pilot-grade auth, stated as such in the
README; production moves them to phone OTP.
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from backend.market import inputs, produce

router = APIRouter(prefix="/api/market", tags=["market"])


def _farm(farm_id: str | None, msisdn: str | None) -> str:
    """A web farmer acts by phone number (so order/offer SMS reach them) or by
    an existing farm id. The number becomes the same salted-hash id every
    phone channel uses, so a web order shows up in the farmer's SMS inbox."""
    if msisdn:
        from backend.channels.identity import InvalidMsisdnError, farm_id_for, mask, normalise
        from backend.memory import store
        try:
            local = normalise(msisdn)
        except InvalidMsisdnError as exc:
            raise HTTPException(422, str(exc))
        fid = farm_id_for(local)
        store.upsert_contact(fid, local, mask(local), "web")
        return fid
    if farm_id:
        return farm_id
    raise HTTPException(422, "farm_id or msisdn is required")


def _fail(exc: Exception) -> HTTPException:
    return HTTPException(422, str(exc))


# --- farmer: inputs -------------------------------------------------------------


@router.get("/inputs")
async def find(product: str, district: str, quantity: float | None = None) -> dict:
    result = inputs.find_inputs(product, district, quantity)
    if result.get("error"):
        raise HTTPException(422, result["error"])
    return result


class OrderIn(BaseModel):
    farm_id: str | None = None
    msisdn: str | None = None
    product_id: str
    packs: int
    payment: str = "cod"


@router.post("/orders")
async def order(payload: OrderIn) -> dict:
    try:
        return inputs.place_order(_farm(payload.farm_id, payload.msisdn), payload.product_id, payload.packs,
                                  payload.payment)
    except inputs.MarketError as exc:
        raise _fail(exc)


@router.get("/orders")
async def orders(farm_id: str | None = None, msisdn: str | None = None) -> dict:
    return {"orders": inputs.farm_orders(_farm(farm_id, msisdn))}


class FarmAction(BaseModel):
    farm_id: str | None = None
    msisdn: str | None = None


@router.post("/orders/{order_id}/cancel")
async def cancel(order_id: int, payload: FarmAction) -> dict:
    try:
        return inputs.set_order_status(order_id, "cancelled", farm_id=_farm(payload.farm_id, payload.msisdn))
    except inputs.MarketError as exc:
        raise _fail(exc)


# --- farmer: produce --------------------------------------------------------------


class ListingIn(BaseModel):
    farm_id: str | None = None
    msisdn: str | None = None
    crop: str
    qty_kg: float
    asking_price_per_kg: float | None = None
    district: str | None = None


@router.post("/listings")
async def create_listing(payload: ListingIn) -> dict:
    try:
        return produce.create_listing(_farm(payload.farm_id, payload.msisdn), payload.crop, payload.qty_kg,
                                      payload.asking_price_per_kg, payload.district)
    except produce.ProduceError as exc:
        raise _fail(exc)


@router.get("/listings")
async def my_listings(farm_id: str | None = None, msisdn: str | None = None) -> dict:
    return {"listings": produce.farm_listings(_farm(farm_id, msisdn))}


@router.get("/price-guide")
async def guide(crop: str) -> dict:
    return produce.price_guide(crop)


class OfferResponse(BaseModel):
    farm_id: str | None = None
    msisdn: str | None = None
    accept: bool


@router.post("/offers/{offer_id}/respond")
async def respond(offer_id: int, payload: OfferResponse) -> dict:
    try:
        return produce.respond_to_offer(_farm(payload.farm_id, payload.msisdn), offer_id, payload.accept)
    except produce.ProduceError as exc:
        raise _fail(exc)


# --- dealers ------------------------------------------------------------------------


class DealerIn(BaseModel):
    name: str
    district: str
    msisdn: str
    upazila: str | None = None


@router.post("/dealers")
async def register_dealer(payload: DealerIn) -> dict:
    try:
        return inputs.register_dealer(payload.name, payload.district, payload.msisdn, payload.upazila)
    except (inputs.MarketError, ValueError) as exc:
        raise _fail(exc)


def _dealer(token: str | None) -> dict:
    try:
        return inputs.dealer_by_token(token or "")
    except inputs.MarketError:
        raise HTTPException(401, "dealer token required")


@router.get("/dealer")
async def dealer_home(x_dealer_token: str | None = Header(default=None)) -> dict:
    return inputs.dealer_view(_dealer(x_dealer_token))


class ProductIn(BaseModel):
    generic: str
    brand_name: str
    pack_size: float
    pack_unit: str
    price_bdt: float
    stock_packs: int
    product_id: str | None = None


@router.put("/dealer/products")
async def upsert_product(payload: ProductIn, x_dealer_token: str | None = Header(default=None)) -> dict:
    dealer = _dealer(x_dealer_token)
    if payload.product_id:
        owned = inputs.db.row("SELECT dealer_id FROM products WHERE product_id = ?", (payload.product_id,))
        if owned and owned["dealer_id"] != dealer["dealer_id"]:
            raise HTTPException(403, "not your product")
    try:
        return inputs.upsert_product(dealer["dealer_id"], payload.generic, payload.brand_name, payload.pack_size,
                                     payload.pack_unit, payload.price_bdt, payload.stock_packs,
                                     price_source=f"dealer listing ({dealer['name']})",
                                     product_id=payload.product_id, is_demo=bool(dealer["is_demo"]))
    except inputs.MarketError as exc:
        raise _fail(exc)


class StatusIn(BaseModel):
    status: str


@router.post("/dealer/orders/{order_id}/status")
async def dealer_status(order_id: int, payload: StatusIn,
                        x_dealer_token: str | None = Header(default=None)) -> dict:
    dealer = _dealer(x_dealer_token)
    try:
        return inputs.set_order_status(order_id, payload.status, dealer_id=dealer["dealer_id"])
    except inputs.MarketError as exc:
        raise _fail(exc)


# --- buyers --------------------------------------------------------------------------


class BuyerIn(BaseModel):
    name: str
    kind: str
    district: str
    msisdn: str


@router.post("/buyers")
async def register_buyer(payload: BuyerIn) -> dict:
    try:
        return produce.register_buyer(payload.name, payload.kind, payload.district, payload.msisdn)
    except (produce.ProduceError, ValueError) as exc:
        raise _fail(exc)


def _buyer(token: str | None) -> dict:
    try:
        return produce.buyer_by_token(token or "")
    except produce.ProduceError:
        raise HTTPException(401, "buyer token required")


@router.get("/buyer")
async def buyer_home(x_buyer_token: str | None = Header(default=None)) -> dict:
    return produce.buyer_view(_buyer(x_buyer_token))


class OfferIn(BaseModel):
    listing_id: int
    price_per_kg: float
    qty_kg: float | None = None
    pickup_date: str | None = None


@router.post("/buyer/offers")
async def buyer_offer(payload: OfferIn, x_buyer_token: str | None = Header(default=None)) -> dict:
    buyer = _buyer(x_buyer_token)
    try:
        return produce.make_offer(buyer["buyer_id"], payload.listing_id, payload.price_per_kg,
                                  payload.qty_kg, payload.pickup_date)
    except produce.ProduceError as exc:
        raise _fail(exc)


@router.get("/districts")
async def districts() -> dict:
    """The 64 districts, Bangla-labelled, for marketplace forms."""
    from backend.tools.ask import district_options
    return {"districts": district_options()}


@router.get("/catalog")
async def catalog() -> dict:
    """Generic inputs the marketplace lists, with Bangla names."""
    from backend.market.catalog import CATEGORY_BN, GENERICS
    return {"inputs": [{"generic": g, "label_bn": v["bn"], "category": v["category"],
                        "category_bn": CATEGORY_BN.get(v["category"], v["category"]), "unit": v["unit"]}
                       for g, v in GENERICS.items()]}
