"""Proactive weather alerts by SMS — Tier 1 advice that reaches a button phone.

For every farm with a registered phone and a saved plan, run the existing
deterministic `check_plan_conflicts` (live Open-Meteo forecast vs the plan's
weather-dependent tasks) and text each NEW conflict once. The SMS is a
template: the rain figure is the forecast value from the alert's provenance,
the task name is the plan's own words. The model writes nothing here.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import date

from backend.branding import BRAND_NAME
from backend.memory import store

from . import sms

log = logging.getLogger("channels.alerts")


def alert_sms_text(alert: dict) -> str:
    d = date.fromisoformat(alert["task_date"])
    rain = (alert.get("provenance") or {}).get("value")
    rain_part = f"{rain:g} মিমি বৃষ্টির পূর্বাভাস" if isinstance(rain, (int, float)) else "ভারী বৃষ্টির পূর্বাভাস"
    return (
        f"{BRAND_NAME} সতর্কতা: {d.day}/{d.month} তারিখে {rain_part} (Open-Meteo)।\n"
        f"'{alert['task']}' কাজটি পরের শুকনো দিনে করুন। জমির পানি নিকাশ দেখুন।"
    )


def scan_once(check=None) -> dict:
    """One pass over all reachable farms. Returns counts for the log/route."""
    if check is None:
        from backend.tools.plan_conflicts import check_plan_conflicts as check
    sent = skipped = errors = 0
    for contact in store.list_contacts():
        farm_id = contact["farm_id"]
        if not store.get_plan(farm_id):
            continue
        try:
            result = check(farm_id)
        except Exception:  # noqa: BLE001 — one farm's failure must not stop the scan
            log.exception("conflict check failed for %s", farm_id)
            errors += 1
            continue
        for alert in result.get("alerts") or []:
            if store.alert_sms_sent(alert["alert_id"]):
                skipped += 1
                continue
            res = sms.send_sms(farm_id, alert_sms_text(alert))
            if res.status != "failed":
                store.mark_alert_sms_sent(alert["alert_id"], farm_id)
                sent += 1
            else:
                errors += 1
    return {"sent": sent, "already_sent": skipped, "errors": errors}


async def run_forever() -> None:
    """Started by the API when ALERT_SMS_ENABLED is true."""
    hours = float(os.environ.get("ALERT_SCAN_HOURS", "6"))
    while True:
        try:
            summary = await asyncio.to_thread(scan_once)
            log.info("alert scan: %s", summary)
        except Exception:  # noqa: BLE001
            log.exception("alert scan failed")
        await asyncio.sleep(max(hours, 0.25) * 3600)
