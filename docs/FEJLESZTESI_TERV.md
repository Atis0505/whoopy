# Whoopy – Fejlesztési terv (sorrend)

A bővítések **ebben a sorrendben** készülnek. Az 1. lépés (ERP kliens) elindult.

| # | Téma | Állapot | Megjegyzés |
|---|------|---------|------------|
| 1 | **ERP → Whoopy kliens** | folyamatban | Adapter + sync API az `e_commerce_erp`-ben |
| 2 | **Fizetés** | várakozik | SimplePay / Stripe (előre utalás helyett/mellett) |
| 3 | **Képfeltöltés** | várakozik | Termékmédia API + tároló |
| 4 | **Webhook-ek** | várakozik | Rendelés / státusz → ERP |
| 5 | **Admin Shopify-szint** | várakozik | Settings, ügyfelek, analitika, CMS |
| 6 | **Merchant Center éles** | várakozik | Teljes taxonomy + GMC |
| 7 | **Prod hardening** | várakozik | Postgres, secret-ek, rate limit, HTTPS |

Használati útmutató: [`HASZNALATI_UTMUTATO.md`](HASZNALATI_UTMUTATO.md) · API: [`API.md`](API.md)
