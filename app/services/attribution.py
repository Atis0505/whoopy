"""UTM + affiliate attribúció (session → cart → order)."""

from __future__ import annotations

import secrets

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AffiliatePartner, Campaign, Cart, Order

UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")


def capture_attribution(request: Request) -> None:
    q = request.query_params
    for key in UTM_KEYS:
        val = (q.get(key) or "").strip()
        if val:
            request.session[key] = val[:128]
    aff = (q.get("aff") or q.get("ref") or q.get("affiliate") or "").strip()
    if aff:
        request.session["affiliate_code"] = aff.upper()[:64]


def session_attribution(session: dict) -> dict[str, str]:
    out = {k: (session.get(k) or "")[:128] for k in UTM_KEYS}
    out["affiliate_code"] = (session.get("affiliate_code") or "")[:64]
    return out


def apply_attribution_to_cart(cart: Cart, session: dict) -> None:
    attr = session_attribution(session)
    for k, v in attr.items():
        if v:
            setattr(cart, k, v)


def copy_attribution_to_order(order: Order, cart: Cart) -> None:
    for k in (*UTM_KEYS, "affiliate_code"):
        setattr(order, k, getattr(cart, k, "") or "")


def record_affiliate_order(db: Session, order: Order) -> None:
    code = (order.affiliate_code or "").strip().upper()
    if not code:
        return
    partner = db.query(AffiliatePartner).filter(AffiliatePartner.code == code, AffiliatePartner.active.is_(True)).first()
    if not partner:
        return
    partner.order_count = int(partner.order_count or 0) + 1
    partner.revenue_total = float(partner.revenue_total or 0) + float(order.grand_total or 0)


def record_affiliate_click(db: Session, code: str) -> AffiliatePartner | None:
    code = (code or "").strip().upper()
    if not code:
        return None
    partner = db.query(AffiliatePartner).filter(AffiliatePartner.code == code, AffiliatePartner.active.is_(True)).first()
    if partner:
        partner.click_count = int(partner.click_count or 0) + 1
        db.commit()
    return partner


def ensure_ab_bucket(session: dict) -> str:
    bucket = session.get("ab_bucket")
    if bucket not in ("A", "B"):
        bucket = "A" if secrets.randbelow(2) == 0 else "B"
        session["ab_bucket"] = bucket
    return bucket


def pick_hero_campaigns(campaigns: list[Campaign], session: dict) -> list[Campaign]:
    """Ha van A és B hero, session bucket szerint választ."""
    heroes = [c for c in campaigns if c.placement == "hero"] if campaigns and hasattr(campaigns[0], "placement") else list(campaigns)
    # callers pass already filtered by placement
    a_list = [c for c in campaigns if (c.ab_group or "A").upper() == "A"]
    b_list = [c for c in campaigns if (c.ab_group or "").upper() == "B"]
    if not b_list:
        return campaigns
    bucket = ensure_ab_bucket(session)
    pool = a_list if bucket == "A" else b_list
    return pool or campaigns


def bump_campaign_impression(db: Session, campaign: Campaign | None) -> None:
    if not campaign:
        return
    campaign.impressions = int(campaign.impressions or 0) + 1
    db.commit()


def bump_campaign_click(db: Session, campaign_id: int) -> Campaign | None:
    c = db.get(Campaign, campaign_id)
    if c:
        c.clicks = int(c.clicks or 0) + 1
        db.commit()
    return c


def utm_report(db: Session, *, limit: int = 50) -> list[dict]:
    from sqlalchemy import func

    rows = (
        db.query(
            Order.utm_source,
            Order.utm_medium,
            Order.utm_campaign,
            func.count(Order.id),
            func.coalesce(func.sum(Order.grand_total), 0.0),
        )
        .filter(Order.utm_source != "")
        .group_by(Order.utm_source, Order.utm_medium, Order.utm_campaign)
        .order_by(func.count(Order.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "utm_source": r[0],
            "utm_medium": r[1],
            "utm_campaign": r[2],
            "orders": r[3],
            "revenue": float(r[4] or 0),
        }
        for r in rows
    ]


def seed_affiliates(db: Session) -> None:
    if db.query(AffiliatePartner).count() == 0:
        db.add(AffiliatePartner(code="PARTNER10", name="Demo partner", commission_percent=10))
        db.add(AffiliatePartner(code="BLOGGER", name="Blog partner", commission_percent=5))
        db.commit()
