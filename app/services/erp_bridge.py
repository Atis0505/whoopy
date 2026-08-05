"""
Whoopy ↔ e_commerce_erp integration contract (planned + stub).

ERP root: C:\\Users\\korom\\Személyes\\e_commerce_erp
ERP ports: API 8010, UI 5181

Whoopy is the customer-facing storefront (whoopy.hu).
ERP remains the catalog/ops brain: partners, feeds, staging→master,
pricing, Pepita/other marketplaces, shipping bindings.

When erp_enabled=True, Whoopy will:
1. Pull sellable master products / offers from ERP
2. Push orders back as Whoopy channel orders
3. Reuse Google taxonomy IDs already mapped in ERP category mappings
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings

# Planned ERP-side tables / entities for the Whoopy sales channel
WHOOPY_ERP_TABLES = {
    "whoopy_channel": "Sales channel registry row (like Pepita marketplace)",
    "whoopy_listings": "ERP master product ↔ Whoopy listing (slug, active, taxonomy)",
    "whoopy_offers": "Supplier/partner offer mirrored for Whoopy storefront",
    "whoopy_orders": "Inbound orders from whoopy.hu checkout",
    "whoopy_order_shipments": "Per-supplier shipments / package legs",
    "whoopy_sync_cursor": "Last successful pull/push watermark",
}


@dataclass
class ErpBridgeStatus:
    enabled: bool
    api_base: str
    message: str


def erp_status() -> ErpBridgeStatus:
    if not settings.erp_enabled:
        return ErpBridgeStatus(
            enabled=False,
            api_base=settings.erp_api_base,
            message="ERP bridge disabled — Whoopy runs on local catalog until sync is turned on.",
        )
    return ErpBridgeStatus(
        enabled=True,
        api_base=settings.erp_api_base,
        message="ERP bridge enabled — storefront should prefer ERP listings API.",
    )


async def ping_erp() -> dict:
    """Best-effort health check; never raises to callers."""
    if not settings.erp_enabled:
        return {"ok": False, "reason": "disabled"}
    try:
        import httpx

        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.erp_api_base.rstrip('/')}/marketplaces/")
            return {"ok": r.status_code < 500, "status_code": r.status_code}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": str(exc)}
