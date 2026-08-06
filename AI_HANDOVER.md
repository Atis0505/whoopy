# AI Handover – Whoopy.hu

> **Olvasd el session elején.** Részletes rendszerkép: [`docs/AI_SYSTEM.md`](docs/AI_SYSTEM.md)  
> Használat (embernek): [`docs/HASZNALATI_UTMUTATO.md`](docs/HASZNALATI_UTMUTATO.md)  
> Frissítve: 2026-08 · Schema **v16** · roadmap **1–21 kész** · folytatás: élesítés + opcionális kód (`AI_HANDOVER` „Mi van még vissza”)

---

## Mi ez?

**Whoopy.hu** — magyar, Google Taxonomy alapú, **többbeszállítós marketplace storefront** (Alza / eMAG / Pepita jellegű UI).

| | |
|--|--|
| **GitHub** | https://github.com/Atis0505/whoopy |
| **Helyi path** | `C:\Users\korom\Személyes\taxonomy-marketplace` |
| **Port** | **8090** (nem 8000) |
| **Stack** | FastAPI + Jinja2 + SQLAlchemy · SQLite (dev) / Postgres (prod) |

Kapcsolódó **ERP** (külön repo): `C:\Users\korom\Személyes\e_commerce_erp` (:8010 API / :5181 UI)  
→ https://github.com/Atis0505/e_commerce_erp · `docs/WHOOPY_ERP_INTEGRATION.md`

A Nokia/`ngNCOM` Cursor workspace **nem** a Whoopy kódja — csak chat/history.

---

## Üzleti modell (ne rontsd el)

- **Partnerek** = források, ahonnan Whoopy **vásárol** — **nem** self-listing eladók.
- **Nincs supplier portal.** Ne építs partner-feltöltő bolt UI-t.
- Egy termékre több Offer (ár / lead / preferált) → buy-box.
- ERP **pushol** katalógust Whoopy felé; Whoopy **nem** pullolja az ERP katalógust.

---

## Gyors indítás

```bash
cd "C:\Users\korom\Személyes\taxonomy-marketplace"
.\.venv\Scripts\activate
python run.py
# tesztek: python -m pytest tests/test_smoke.py -q
```

Demo: `admin@whoopy.local` / `admin1234` · `dolgozo@…` / `worker123` · `vasarlo@…` / `vasarlo123`  
API key (dev): `whoopy-dev-api-key-change-me`

Docker: `docker compose up --build` — `docs/DEPLOY.md`.

---

## Hogyan haladtunk (roadmap 1–21 = kész)

| # | Csomag | Doc |
|---|--------|-----|
| 1–8 | ERP kliens, fizetés, képek, webhook, admin, merchant, prod, partner ops | `PARTNEREK`, `FIZETES`, `KEPEK`, … |
| 9–13 | Autosync, CDN, SimplePay sandbox, Docker, smoke/S3/orders | `DEPLOY`, `PROD` |
| 14 | EU webshop (GDPR banner v1, SEO, ÁFA, invoice HTML, track, FAQ…) | `EU_SHOP.md` |
| 15 | Checkout E2E smoke + **Számlázz.hu Agent stub** | `SZAMLAZZ.md` |
| 16 | Vásárlói UX (search, pickup, billing, gift, loyalty, compare…) | `UX.md` |
| 17 | Marketing (Meta + Árukereső, UTM, affiliate, hero A/B) | `MARKETING.md` |
| 18 | **Logisztika + Compliance** (futár/RMA stub, warehouse, CMP, GDPR export/törlés, B2B ÁFA, Omnibus) | `LOGISTICS_COMPLIANCE.md` |
| 19 | **Storefront ops** (announcement, social ticker, maintenance 1-gomb, kampány toggle, free-ship, responsive) | `STOREFRONT_OPS.md` |
| 20 | **Omnibus + ismétlődő rendelés** (PriceHistory auto-log/riporter/guard, Subscription) | `OMNIBUS_SUBSCRIPTIONS.md` |
| 21 | **Katalógus skálázás** (pagination, indexek, sitemap chunk) | `CATALOG_SCALE.md` |

Tipikus commit minta a `main`-en: … → omnibus/subscriptions → catalog scale.

**Schema:** `app/bootstrap.py` `SCHEMA_VERSION = "16"` + `.schema_version`.  
Dev SQLite: hiányzó kötelező oszlop → wipe; version bump → `create_all` + additive ALTER/INDEX (zárolt DB-nél wipe nélkül). Prod/Postgres: **soha nem wipe**.

---

## Hol van mi (gyors térkép)

| Terület | Hol |
|---------|-----|
| Bolt | `app/routers/store.py`, `templates/store/` |
| Katalógus lista / lapozó | `services/catalog.py` · `templates/partials/pager.html` |
| EU extras | `routers/eu_shop.py` (sitemap chunk is) |
| UX | `routers/customer_ux.py`, `services/customer_ux.py` |
| Compliance / Omnibus | `routers/compliance.py`, `services/compliance.py`, `services/vat.py` |
| Ismétlődő rendelés | `routers/subscriptions.py`, `services/subscriptions.py` |
| Futár / RMA | `services/carriers.py`, `services/rma.py` |
| Marketing | `services/marketing_feeds.py`, `services/attribution.py` |
| Számlázz | `services/szamlazz.py` → `data/szamlazz_outbox/` |
| Admin | `routers/admin*.py` · `/admin/price-history` · `/admin/subscriptions` |
| Smoke | `tests/test_smoke.py` (~21 teszt) |

Outbox stubok (gitignore): `data/email_outbox/`, `szamlazz_outbox/`, `carrier_outbox/`, `rma_outbox/`.

---

## Mi van még vissza — mivel érdemes folytatni

A **1–21 feature sor kész.** Nincs kötelező következő kód-csomag. Prioritás:

### A) Élesítés (külső függőség — üzleti kulcs / DNS kell)

| # | Téma | Állapot most | Doc |
|---|------|--------------|-----|
| 1 | **Domain + TLS** (whoopy.hu) | config kész, DNS kell | `DEPLOY.md`, `PROD.md` |
| 2 | **SimplePay éles** merchant + publikus IPN | sandbox OK | `FIZETES.md` |
| 3 | **Számlázz Agent kulcs** | dry-run / outbox stub | `SZAMLAZZ.md` |
| 4 | **Éles futár / csomagpont** (GLS, Foxpost, Packeta) | outbox stub | `LOGISTICS_COMPLIANCE.md` |
| 5 | **VIES** élő adószám | csak formátum | `services/vat.py` |

### B) Opcionális kód (ha még feature kell kulcs nélkül)

| # | Téma | Miért |
|---|------|--------|
| 1 | **Abandoned-cart** értesítés erősítés | kosárnak gyakran nincs e-mail → guest e-mail a kosárban / admin digest |
| 2 | **Ismétlődő rendelés + kártya** | most COD/`pending` stub; éles payment token kell |
| 3 | **Feed chunk / stream** (Google/Meta) | 40–80k SKU-nál XML egyben nehéz; pagination már a HTML listákon megvan |
| 4 | **Postgres éles** + connection pool | SQLite csak demó/dev |
| 5 | **VIES HTTP kliens** (flag mögött) | formátum után élő EU check, timeout/fallback-kal |

### C) Szándékosan NEM

- Theme editor / teljes Shopify A/B UI  
- Supplier portal / partner self-listing  
- Whoopy → ERP katalógus **pull**  
- Prod schema wipe  

---

## ERP kötés (rövid)

- Whoopy Management API: `/api/v1/*` + `X-API-Key`
- ERP: `/api/v1/whoopy-sync/*` + autosync (`WHOOPY_AUTOSYNC_ENABLED`)
- Whoopy → ERP webhook → JSONL inbox
- Admin: `/admin/integrations` (őszinte státusz)

---

## Új session checklist

1. `AI_HANDOVER.md` → `docs/AI_SYSTEM.md` → érintett feature doc  
2. `python run.py` · `/admin/integrations`  
3. Modellváltozás → `SCHEMA_VERSION` növelés  
4. Commit Whoopy **és** ERP külön repo; ne `.env` / `*.db` / uploads  
5. Smoke: `pytest tests/test_smoke.py -q`

---

## Doc index

| Fájl | Szerep |
|------|--------|
| `AI_HANDOVER.md` | **Ez** — session start |
| `docs/AI_SYSTEM.md` | Teljes rendszer + roadmap |
| `docs/HASZNALATI_UTMUTATO.md` | Magyar használat |
| `docs/FEJLESZTESI_TERV.md` | 1–21 tábla |
| `docs/LOGISTICS_COMPLIANCE.md` | v13 logisztika/compliance |
| `docs/STOREFRONT_OPS.md` | v14 banner / ticker / maintenance |
| `docs/OMNIBUS_SUBSCRIPTIONS.md` | v15 ártörténet + ismétlés |
| `docs/CATALOG_SCALE.md` | v16 pagination / index / sitemap |
| `docs/UX.md` / `MARKETING.md` / `EU_SHOP.md` / `SZAMLAZZ.md` | Feature csomagok |
| `docs/PARTNEREK.md` / `API.md` / `ADMIN.md` / `PROD.md` / `DEPLOY.md` | Ops |
