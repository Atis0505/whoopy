"""ÁFA segédek — Whoopy árak bruttók (EU B2C)."""

from __future__ import annotations


def split_gross(gross: float, rate_percent: float) -> tuple[float, float, float]:
    """Vissza: (net, tax, gross_rounded)."""
    rate = float(rate_percent or 0)
    gross = float(gross or 0)
    if rate <= 0 or gross <= 0:
        return round(gross, 2), 0.0, round(gross, 2)
    tax = round(gross * rate / (100.0 + rate), 2)
    net = round(gross - tax, 2)
    return net, tax, round(gross, 2)


# Egyszerű OSS stub: ország → ÁFA % (B2C, nem B2B reverse charge)
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


def vat_rate_for_country(country: str, fallback: float = 27.0) -> float:
    return float(EU_VAT_RATES.get((country or "").upper(), fallback))
