"""
Whoopy ↔ e_commerce_erp bridge.

Architektúra (2026):
- Katalógus sync iránya: **ERP → Whoopy** (Management API + whoopy-sync autosync)
- Rendelés: Whoopy outbound webhook → ERP `/webhooks/whoopy` (+ ERP poll GET orders)
- Ez a modul: státusz / ping / ERP autosync trigger (ha erp_enabled)

ERP: C:\\Users\\korom\\Személyes\\e_commerce_erp (:8010)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import httpx

from app.config import settings


@dataclass
class ErpBridgeStatus:
    enabled: bool
    api_base: str
    message: str
    webhook_enabled: bool = False
    webhook_url: str = ""


def erp_status() -> ErpBridgeStatus:
    if not settings.erp_enabled:
        return ErpBridgeStatus(
            enabled=False,
            api_base=settings.erp_api_base,
            message="ERP bridge kikapcsolva — katalógust az ERP whoopy-sync pusholja (ajánlott).",
            webhook_enabled=settings.webhook_enabled,
            webhook_url=settings.webhook_url,
        )
    return ErpBridgeStatus(
        enabled=True,
        api_base=settings.erp_api_base,
        message="ERP bridge be — ping / autosync trigger elérhető az admin Integrációknál.",
        webhook_enabled=settings.webhook_enabled,
        webhook_url=settings.webhook_url,
    )


async def ping_erp() -> dict[str, Any]:
    """Best-effort health check; never raises to callers."""
    if not settings.erp_enabled:
        return {"ok": False, "reason": "disabled"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.erp_api_base.rstrip('/')}/whoopy-sync/status")
            data: Any
            try:
                data = r.json()
            except Exception:
                data = {"raw": r.text[:200]}
            return {"ok": r.status_code < 500, "status_code": r.status_code, "body": data}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": str(exc)}


async def trigger_erp_autosync(limit: int = 100) -> dict[str, Any]:
    """Meghívja az ERP POST /whoopy-sync/autosync végpontot."""
    if not settings.erp_enabled:
        return {"ok": False, "reason": "ERP_ENABLED=false"}
    url = f"{settings.erp_api_base.rstrip('/')}/whoopy-sync/autosync"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, params={"limit": limit})
            try:
                body = r.json()
            except Exception:
                body = {"raw": r.text[:500]}
            return {"ok": r.status_code < 400, "status_code": r.status_code, "result": body}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": str(exc)}


def status_dict() -> dict[str, Any]:
    return asdict(erp_status())
