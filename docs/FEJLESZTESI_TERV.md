# Whoopy – Fejlesztési terv (sorrend)

A bővítések **ebben a sorrendben** készülnek. Az 1. lépés (ERP kliens) elindult.

| # | Téma | Állapot | Megjegyzés |
|---|------|---------|------------|
| 1 | **ERP → Whoopy kliens** | kész | Adapter + `/whoopy-sync` az ERP-ben |
| 2 | **Fizetés** | kész | Demo + Stripe + SimplePay (`docs/FIZETES.md`) |
| 3 | **Képfeltöltés** | kész | Helyi media + API + admin (`docs/KEPEK.md`) |
| 4 | **Webhook-ek** | kész | Whoopy → ERP (`docs/WEBHOOKOK.md`) |
| 5 | **Admin Shopify-szint** | kész | Settings, ügyfelek, analitika, CMS… (`docs/ADMIN.md`) |
| 6 | **Merchant Center éles** | kész | Feed validáció + taxonomy import (`docs/MERCHANT.md`) |
| 7 | **Prod hardening** | kész | Secrets, Postgres, rate limit, HTTPS (`docs/PROD.md`) |
| 8 | **Belső partner ops** | kész | Staging, feed, árazás, beszerzés, dedup, KPI (`docs/PARTNEREK.md`) — **nincs** supplier portal |
| 9 | **ERP master autosync** | kész | ERP `WHOOPY_AUTOSYNC_*` + `/whoopy-sync/autosync` |
| 10 | **CDN media base** | kész | `MEDIA_PUBLIC_BASE` (`docs/KEPEK.md`) |
| 11 | **SimplePay sandbox** | kész | IPN signature + fallback flag (`docs/FIZETES.md`) |
| 12 | **Deploy / Docker** | kész | `Dockerfile`, `docker-compose.yml`, `docs/DEPLOY.md` |
| 13 | **whoopy_orders + presence + S3 + smoke** | kész | ERP inbound DB, offer_id map, R2/S3, `tests/test_smoke.py` |

**A tervezett bővítési sor kész.** További ötletek: checkout E2E, éles SimplePay merchant, domain DNS.

Rendszerleírás AI-nak: [`AI_SYSTEM.md`](AI_SYSTEM.md) · Használat: [`HASZNALATI_UTMUTATO.md`](HASZNALATI_UTMUTATO.md) · API: [`API.md`](API.md) · Fizetés: [`FIZETES.md`](FIZETES.md) · Képek: [`KEPEK.md`](KEPEK.md) · Webhook: [`WEBHOOKOK.md`](WEBHOOKOK.md) · Admin: [`ADMIN.md`](ADMIN.md) · Merchant: [`MERCHANT.md`](MERCHANT.md) · Prod: [`PROD.md`](PROD.md) · Deploy: [`DEPLOY.md`](DEPLOY.md) · Partnerek: [`PARTNEREK.md`](PARTNEREK.md)
