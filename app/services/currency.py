from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import CurrencyRate

DEFAULT_RATES = [
    ("HUF", 1.0, "Ft"),
    ("EUR", 395.0, "€"),
    ("USD", 365.0, "$"),
    ("PLN", 92.0, "zł"),
    ("RON", 79.0, "lei"),
]


def ensure_currency_rates(db: Session) -> None:
    if db.query(CurrencyRate).count() > 0:
        return
    for code, rate, symbol in DEFAULT_RATES:
        db.add(CurrencyRate(code=code, rate_to_huf=rate, symbol=symbol, active=True))
    db.commit()


def get_rate(db: Session, code: str) -> CurrencyRate | None:
    return db.query(CurrencyRate).filter(CurrencyRate.code == code.upper(), CurrencyRate.active.is_(True)).first()


def convert_from_huf(db: Session, amount_huf: float, currency: str) -> float:
    currency = (currency or "HUF").upper()
    if currency == "HUF":
        return round(amount_huf, 2)
    rate = get_rate(db, currency)
    if not rate or rate.rate_to_huf <= 0:
        return round(amount_huf, 2)
    return round(amount_huf / rate.rate_to_huf, 2)


def format_money(db: Session, amount_huf: float, currency: str) -> str:
    currency = (currency or "HUF").upper()
    value = convert_from_huf(db, amount_huf, currency)
    rate = get_rate(db, currency)
    symbol = rate.symbol if rate else currency
    if currency == "HUF":
        return f"{value:,.0f} {symbol}".replace(",", " ")
    return f"{symbol}{value:,.2f}"
