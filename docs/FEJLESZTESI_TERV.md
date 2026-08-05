# Whoopy – Fejlesztési terv (sorrend)

A bővítések **ebben a sorrendben** készülnek. Az 1. lépés (ERP kliens) elindult.

| # | Téma | Állapot | Megjegyzés |
|---|------|---------|------------|
| 1 | **ERP → Whoopy kliens** | kész | Adapter + `/whoopy-sync` az ERP-ben |
| 2 | **Fizetés** | kész | Demo + Stripe + SimplePay (`docs/FIZETES.md`) |
| 3 | **Képfeltöltés** | várakozik | Termékmédia API + tároló |
| 4 | **Webhook-ek** | várakozik | Rendelés / státusz → ERP |
| 5 | **Admin Shopify-szint** | várakozik | Settings, ügyfelek, analitika, CMS |
| 6 | **Merchant Center éles** | várakozik | Teljes taxonomy + GMC |
| 7 | **Prod hardening** | várakozik | Postgres, secret-ek, rate limit, HTTPS |

Használati útmutató: [`HASZNALATI_UTMUTATO.md`](HASZNALATI_UTMUTATO.md) · API: [`API.md`](API.md) · Fizetés: [`FIZETES.md`](FIZETES.md)
