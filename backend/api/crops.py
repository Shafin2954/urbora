"""Authenticated crop index backed by Supabase RLS.

The Postgres table deliberately stores identity and ownership only. Farm
profile fields and conversation history stay in the established SQLite store.
Every database request carries the caller's Supabase access token, so RLS—not
an application-side user filter—decides which rows exist for that caller.
"""

from __future__ import annotations

import os
from uuid import uuid4

import httpx
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from backend.memory.store import get_farm, get_session_messages
from backend.tools.farm_memory import remember_farm

router = APIRouter()

_PROFILE_FIELDS = {"district", "area", "area_unit", "soil_type", "water_source", "budget_bdt", "season"}


class CropPatch(BaseModel):
    crop: str | None = Field(default=None, max_length=80)
    title: str | None = Field(default=None, max_length=80)
    district: str | None = None
    area: float | None = None
    area_unit: str | None = None
    soil_type: str | None = None
    water_source: str | None = None
    budget_bdt: float | None = None
    season: str | None = None


def _settings() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    if not url or not anon_key:
        raise HTTPException(status_code=503, detail="Supabase is not configured")
    return url, anon_key


def _token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Supabase access token")
    return authorization.split(" ", 1)[1]


async def _request(method: str, path: str, token: str, *, json: object | None = None, params: dict | None = None) -> object:
    url, anon_key = _settings()
    headers = {"apikey": anon_key, "Authorization": f"Bearer {token}"}
    if method in {"POST", "PATCH"}:
        headers["Prefer"] = "return=representation"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.request(method, f"{url}{path}", headers=headers, json=json, params=params)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail="Supabase request failed")
    return response.json() if response.content else None


async def _owned_crop(crop_id: str, token: str) -> dict:
    rows = await _request("GET", "/rest/v1/crops", token, params={"select": "*", "id": f"eq.{crop_id}"})
    if not rows:
        raise HTTPException(status_code=404, detail="Crop not found")
    return rows[0]


def _merged(row: dict) -> dict:
    profile = get_farm(row["farm_id"]) or {}
    return {
        **row,
        "profile": {key: profile.get(key) for key in _PROFILE_FIELDS if profile.get(key) is not None},
        "label": row.get("crop") or profile.get("last_crop") or "New consultation",
        "title": row.get("title") or "New consultation",
    }


@router.get("/api/crops")
async def list_crops(authorization: str | None = Header(default=None)) -> list[dict]:
    token = _token(authorization)
    rows = await _request("GET", "/rest/v1/crops", token, params={"select": "*", "order": "updated_at.desc"})
    return [_merged(row) for row in rows]


@router.post("/api/crops", status_code=status.HTTP_201_CREATED)
async def create_crop(authorization: str | None = Header(default=None)) -> dict:
    token = _token(authorization)
    user = await _request("GET", "/auth/v1/user", token)
    row = {
        "user_id": user["id"],
        "farm_id": str(uuid4()),
        "session_id": str(uuid4()),
        "crop": None,
    }
    created = await _request("POST", "/rest/v1/crops", token, json=row)
    return _merged(created[0])


@router.patch("/api/crops/{crop_id}")
async def update_crop(crop_id: str, patch: CropPatch, authorization: str | None = Header(default=None)) -> dict:
    token = _token(authorization)
    row = await _owned_crop(crop_id, token)
    changes = patch.model_dump(exclude_unset=True)
    profile = {key: value for key, value in changes.items() if key in _PROFILE_FIELDS and value is not None}
    if profile:
        remember_farm(row["farm_id"], **profile)
    index_changes = {key: changes[key] for key in ("crop", "title") if key in changes}
    if index_changes:
        updated = await _request("PATCH", "/rest/v1/crops", token, json=index_changes, params={"id": f"eq.{crop_id}"})
        row = updated[0]
    return _merged(row)


@router.delete("/api/crops/{crop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crop(crop_id: str, authorization: str | None = Header(default=None)) -> None:
    token = _token(authorization)
    await _owned_crop(crop_id, token)
    await _request("DELETE", "/rest/v1/crops", token, params={"id": f"eq.{crop_id}"})


@router.get("/api/sessions/{session_id}")
async def session_messages(session_id: str, authorization: str | None = Header(default=None)) -> dict:
    token = _token(authorization)
    rows = await _request("GET", "/rest/v1/crops", token, params={"select": "id", "session_id": f"eq.{session_id}"})
    if not rows:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"messages": get_session_messages(session_id)}
