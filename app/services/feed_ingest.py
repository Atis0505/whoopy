"""Partner feed ingest → staging (CSV / JSON / URL). Mi húzzuk — ők nem hirdetnek."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import FeedRun, FeedSource, StagingListing
from app.services.pricing_engine import compute_list_price


DEFAULT_MAP = {
    "sku": "sku",
    "gtin": "gtin",
    "title": "title",
    "description": "description",
    "brand": "brand",
    "image_url": "image_url",
    "price": "price",
    "cost": "cost",
    "stock": "stock",
    "lead_days": "lead_days",
}


def _map(field_map_raw: str) -> dict[str, str]:
    if not field_map_raw.strip():
        return dict(DEFAULT_MAP)
    try:
        data = json.loads(field_map_raw)
        if isinstance(data, dict):
            merged = dict(DEFAULT_MAP)
            merged.update({k: str(v) for k, v in data.items()})
            return merged
    except json.JSONDecodeError:
        pass
    return dict(DEFAULT_MAP)


def _get(row: dict[str, Any], key: str, fmap: dict[str, str], default: Any = "") -> Any:
    src = fmap.get(key, key)
    if src in row and row[src] not in (None, ""):
        return row[src]
    # case-insensitive
    lower = {str(k).lower(): v for k, v in row.items()}
    return lower.get(str(src).lower(), default)


def _float(v: Any, default: float = 0.0) -> float:
    try:
        return float(str(v).replace(",", ".").replace(" ", ""))
    except (TypeError, ValueError):
        return default


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(float(str(v).replace(",", ".").replace(" ", "")))
    except (TypeError, ValueError):
        return default


def rows_from_csv(content: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(content))
    return [dict(r) for r in reader]


def rows_from_json(content: str) -> list[dict[str, Any]]:
    data = json.loads(content)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "products", "data", "rows"):
            if isinstance(data.get(key), list):
                return data[key]
    raise ValueError("JSON feed: lista vagy items/products/data tömb kell")


def fetch_url(url: str) -> str:
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def ingest_rows(db: Session, source: FeedSource, rows: list[dict[str, Any]]) -> FeedRun:
    fmap = _map(source.field_map)
    run = FeedRun(feed_source_id=source.id, started_at=datetime.utcnow())
    db.add(run)
    db.flush()
    ok = 0
    failed = 0
    errors: list[str] = []

    for i, raw in enumerate(rows):
        try:
            title = str(_get(raw, "title", fmap, "")).strip()
            sku = str(_get(raw, "sku", fmap, "")).strip()
            gtin = str(_get(raw, "gtin", fmap, "")).strip()
            if not title and not sku and not gtin:
                failed += 1
                errors.append(f"[{i}] üres sor")
                continue
            if not title:
                title = sku or gtin or f"Partner tétel {i}"
            cost = _float(_get(raw, "cost", fmap, 0))
            list_price = _float(_get(raw, "price", fmap, 0))
            if list_price <= 0 and cost > 0:
                list_price = compute_list_price(db, cost, supplier_id=source.supplier_id)
            stock = _int(_get(raw, "stock", fmap, 0))
            lead = _int(_get(raw, "lead_days", fmap, 2), 2)
            db.add(
                StagingListing(
                    supplier_id=source.supplier_id,
                    feed_source_id=source.id,
                    status="pending",
                    gtin=gtin,
                    sku=sku,
                    title=title,
                    description=str(_get(raw, "description", fmap, "")),
                    brand=str(_get(raw, "brand", fmap, "")),
                    image_url=str(_get(raw, "image_url", fmap, "")),
                    cost_price=cost,
                    list_price=list_price,
                    stock=stock,
                    lead_days=lead,
                )
            )
            ok += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            errors.append(f"[{i}] {exc}")

    run.rows_ok = ok
    run.rows_failed = failed
    run.success = failed == 0 and ok > 0
    run.message = "; ".join(errors[:20])
    run.finished_at = datetime.utcnow()
    source.last_run_at = run.finished_at
    source.last_status = "ok" if run.success else "partial" if ok else "error"
    source.last_message = f"+{ok} staging, fail={failed}"
    db.commit()
    db.refresh(run)
    return run


def run_feed_source(db: Session, source_id: int, csv_text: str | None = None) -> FeedRun:
    source = db.get(FeedSource, source_id)
    if not source:
        raise ValueError("Feed source nem található")
    if csv_text is not None:
        text = csv_text.strip()
        if source.source_type == "json" or text[:1] in ("[", "{"):
            rows = rows_from_json(text)
        else:
            rows = rows_from_csv(csv_text)
    elif source.source_type in ("url_json", "json") and source.url:
        text = fetch_url(source.url)
        rows = rows_from_json(text)
    elif source.source_type == "csv" and source.url:
        text = fetch_url(source.url)
        rows = rows_from_csv(text)
    else:
        raise ValueError("Nincs bemenet — tölts CSV-t vagy állíts URL-t")
    return ingest_rows(db, source, rows)
