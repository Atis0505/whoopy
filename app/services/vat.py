"""ÁFA segédek — Whoopy árak bruttók (EU B2C) + B2B reverse charge stub."""

from __future__ import annotations

import re


def split_gross(gross: float, rate_percent: float) -> tuple[float, float, float]:
    """Vissza: (net, tax, gross_rounded)."""
    rate = float(rate_percent or 0)
    gross = float(gross or 0)
    if rate <= 0 or gross <= 0:
        return round(gross, 2), 0.0, round(gross, 2)
    tax = round(gross * rate / (100.0 + rate), 2)
    net = round(gross - tax, 2)
    return net, tax, round(gross, 2)


EU_VAT_RATES = {
    "HU": 27.0,
    "AT": 20.0,
    "DE": 19.0,
    "SK": 20.0,
    "RO": 19.0,
    "PL": 23.0,
    "CZ": 21.0,
    "FR": 20.0,
    "IT": 22.0,
    "ES": 21.0,
    "NL": 21.0,
    "BE": 21.0,
}

EU_COUNTRIES = set(EU_VAT_RATES.keys()) | {
    "SE", "FI", "DK", "IE", "PT", "GR", "LU", "EE", "LV", "LT", "SI", "HR", "BG", "CY", "MT",
}


def vat_rate_for_country(country: str, fallback: float = 27.0) -> float:
    return float(EU_VAT_RATES.get((country or "").upper(), fallback))


def normalize_eu_vat(vat_id: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (vat_id or "").upper())


def validate_eu_vat_format(vat_id: str) -> bool:
    """Formátum-ellenőrzés (nem VIES live)."""
    v = normalize_eu_vat(vat_id)
    if len(v) < 4 or len(v) > 14:
        return False
    cc = v[:2]
    if cc not in EU_COUNTRIES and not cc.isalpha():
        return False
    return bool(re.match(r"^[A-Z]{2}[A-Z0-9]{2,12}$", v))


def effective_vat_rate(
    *,
    country: str,
    fallback: float = 27.0,
    is_b2b: bool = False,
    buyer_vat_id: str = "",
    seller_country: str = "HU",
) -> tuple[float, bool]:
    """
    Vissza: (rate_percent, reverse_charge).
    B2B + érvényes EU ÁFA + más ország → reverse charge (0%).
    """
    country = (country or seller_country or "HU").upper()
    seller_country = (seller_country or "HU").upper()
    if is_b2b and validate_eu_vat_format(buyer_vat_id):
        vat_cc = normalize_eu_vat(buyer_vat_id)[:2]
        if vat_cc in EU_COUNTRIES and vat_cc != seller_country and country != seller_country:
            return 0.0, True
        if vat_cc in EU_COUNTRIES and vat_cc != seller_country:
            return 0.0, True
    return vat_rate_for_country(country, fallback), False
