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
| 14 | **EU webshop csomag** | kész | GDPR, SEO, ÁFA, invoice, e-mail, track, contact, FAQ, filters, wishlist, returns, reviews (`docs/EU_SHOP.md`) |
| 15 | **Checkout E2E + Számlázz stub** | kész | Smoke checkout flow; Számlázz.hu Agent dry-run/éles hook (`docs/SZAMLAZZ.md`) |
| 16 | **Vásárlói élmény csomag** | kész | Keresés, csomagpont, billing cím, track token, abandoned/newsletter mail, compare/recent, variáns, gift, loyalty, chat (`docs/UX.md`) |
| 17 | **Marketing csomag** | kész | Meta + Árukereső feed, UTM/affiliate, hero A/B (`docs/MARKETING.md`) |
| 18 | **Logisztika + Compliance** | kész | Futár/RMA stub, warehouse/partial fulfill, CMP, GDPR, B2B ÁFA, Omnibus (`docs/LOGISTICS_COMPLIANCE.md`) |

**A tervezett bővítési sor (1–18) kész.**  
Következő lépések inkább **élesítés**: SimplePay merchant, domain/TLS, Számlázz kulcs, éles futár/csomagpont API — lásd `AI_HANDOVER.md` „Mi van még vissza”.

Rendszerleírás AI-nak: [`AI_SYSTEM.md`](AI_SYSTEM.md) · Logisztika/Compliance: [`LOGISTICS_COMPLIANCE.md`](LOGISTICS_COMPLIANCE.md) · Marketing: [`MARKETING.md`](MARKETING.md) · UX: [`UX.md`](UX.md) · EU shop: [`EU_SHOP.md`](EU_SHOP.md) · Számlázz: [`SZAMLAZZ.md`](SZAMLAZZ.md) · Használat: [`HASZNALATI_UTMUTATO.md`](HASZNALATI_UTMUTATO.md) · API: [`API.md`](API.md) · Fizetés: [`FIZETES.md`](FIZETES.md) · Képek: [`KEPEK.md`](KEPEK.md) · Webhook: [`WEBHOOKOK.md`](WEBHOOKOK.md) · Admin: [`ADMIN.md`](ADMIN.md) · Merchant: [`MERCHANT.md`](MERCHANT.md) · Prod: [`PROD.md`](PROD.md) · Deploy: [`DEPLOY.md`](DEPLOY.md) · Partnerek: [`PARTNEREK.md`](PARTNEREK.md)
