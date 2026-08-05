# Fizetés (Whoopy)

Online fizetés a checkout után, ha a kosárban **Online / bankkártya** (`prepaid`) van kiválasztva.

## Működés vásárlói oldalon

1. Kosár → fizetési mód: **Online / bankkártya** (vagy utánvét / számla).
2. Checkout űrlap → rendelés létrejön (`payment_status=awaiting`).
3. Átirányítás: `/pay/{rendelésszám}`
4. Provider:
   - **demo** (alap): `/pay/.../demo` — „Fizetés sikeres” gomb
   - **Stripe**: Checkout Session → Stripe oldal
   - **SimplePay**: OTP start → SimplePay oldal
5. Visszatérés: `/order/{szám}?pay=ok` (vagy failed / cancelled / pending)

Utánvét (`cod`) és számla (`invoice`) esetén **nincs** online kapu — a rendelés `pending` marad.

## Konfiguráció (env / `app/config.py`)

```env
PAYMENT_PROVIDER=auto
PUBLIC_BASE_URL=http://127.0.0.1:8090

# Stripe (opcionális)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_CURRENCY=huf

# OTP SimplePay (opcionális)
SIMPLEPAY_MERCHANT=...
SIMPLEPAY_SECRET_KEY=...
SIMPLEPAY_SANDBOX=true
SIMPLEPAY_CURRENCY=HUF
```

`PAYMENT_PROVIDER`:

| Érték | Viselkedés |
|-------|------------|
| `auto` | Stripe kulcs → stripe; különben SimplePay → simplepay; különben **demo** |
| `demo` | Mindig demo oldal |
| `stripe` | Stripe (kulcs nélkül visszaesik demo-ra) |
| `simplepay` | SimplePay (kulcs nélkül demo) |

## Webhook / IPN

| Provider | URL |
|----------|-----|
| Stripe | `POST /pay/webhook/stripe` |
| SimplePay | `POST /pay/webhook/simplepay` |

Állítsd be a provider dashboardon a `PUBLIC_BASE_URL` alapján.

## Fejlesztői megjegyzés

- Schema mezők: `Order.payment_status`, `payment_provider`, `payment_ref`, `paid_at` (schema **v5**).
- Kód: `app/services/payments.py`, `app/routers/payments.py`
