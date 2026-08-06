# Whoopy rendszerleírás — AI / fejlesztői handover

> Célközönség: **másik AI agent** vagy új fejlesztő, aki nulláról folytatja a Whoopy ökoszisztémát.  
> Frissítve: 2026-08 · Schema Whoopy **v9**

---

## 1. Mi ez, mi a cél?

**Whoopy.hu** egy magyar, Google Taxonomy alapú **multi-supplier marketplace storefront**.

| Szerep | Projekt | Port | GitHub |
|--------|---------|------|--------|
| Vevői bolt + admin + Management API | `taxonomy-marketplace` | **8090** | https://github.com/Atis0505/whoopy |
| Katalógus / ops ERP (partnerek, feed, más piacterek) | `e_commerce_erp` | **8010** API / **5181** UI | https://github.com/Atis0505/e_commerce_erp |

### Üzleti modell (kritikus)

- A „partnerek” **források, ahonnan a Whoopy vásárol** — **nem** self-listing eladók.
- **Nincs supplier portal.** Partnerek nem hirdetnek a bolton.
- Dropship csak ha a partner kínálja; Whoopy dönt.
- Ugyanarra a termékre több partner-ajánlat lehet (ár / lead / preferált) → buy-box.
- Belső ops: staging review, feed ingest, árazás, beszerzési nézet, GTIN dedup, KPI.

---

## 2. Hogyan készült (architektúra)

```
[Partner CSV/JSON/URL] → Whoopy Feed → Staging → Publish → Product+Offer
                              ↑
[ERP master] ──whoopy-sync───┘  (push, autosync)
                              ↓
[Vásárló] → Storefront → Checkout → Payment → Order
                              ↓
                    Outbound webhook → ERP inbox
```

**Stack (Whoopy):** FastAPI + Jinja2 + SQLAlchemy + SQLite (dev) / Postgres (prod).  
**Auth bolt:** session cookie. **API:** `X-API-Key`.  
**Schema bump:** `.schema_version` + `app/bootstrap.py` — **dev SQLite wipe** version change-nél; **prod/Postgres soha nem wipe**.

### Fő modulok (Whoopy)

| Terület | Hol |
|---------|-----|
| Storefront | `app/routers/store.py`, `app/templates/store/` |
| Admin (Shopify-szerű) | `app/routers/admin.py`, `admin_extra.py`, `admin_marketplace.py` |
| Management API | `app/routers/api_v1.py` → `/api/v1/*` |
| Fizetés | `app/services/payments.py`, `app/routers/payments.py` |
| Webhook out | `app/services/webhooks.py` |
| Partner ops | `services/{staging,feed_ingest,pricing_engine,procurement,dedup}.py` |
| Képek | `app/services/media.py` + `/media/products` |
| Merchant | `app/services/google_feed.py` |
| ERP bridge | `app/services/erp_bridge.py` (ping + autosync trigger) |
| EU shop | `app/routers/eu_shop.py`, `services/{vat,email}.py` · `docs/EU_SHOP.md` |

### ERP oldal

| Terület | Hol |
|---------|-----|
| Adapter | `app/services/marketplace/whoopy.py` |
| Sync service | `app/services/whoopy_sync_service.py` (+ `autosync_from_master`) |
| HTTP | `/api/v1/whoopy-sync/*` |
| Webhook in | `POST /api/v1/webhooks/whoopy` → `data/whoopy_webhook_inbox.jsonl` |
| Autosync job | APScheduler + Celery `whoopy_autosync_task` |

---

## 3. Demo belépők (Whoopy)

| Szerep | Email | Jelszó |
|--------|-------|--------|
| admin | `admin@whoopy.local` | `admin1234` |
| dolgozó | `dolgozo@whoopy.local` | `worker123` |
| vásárló | `vasarlo@whoopy.local` | `vasarlo123` |

API key (dev): `whoopy-dev-api-key-change-me`

---

## 4. Dokumentum térkép

| Doc | Tartalom |
|-----|----------|
| `AI_HANDOVER.md` | Rövid session start |
| `docs/AI_SYSTEM.md` | **Ez a fájl** — teljes rendszerkép |
| `docs/HASZNALATI_UTMUTATO.md` | Magyar használat |
| `docs/FEJLESZTESI_TERV.md` | Roadmap állapot |
| `docs/API.md` | Management API |
| `docs/PARTNEREK.md` | Belső partner ops |
| `docs/EU_SHOP.md` | GDPR, SEO, ÁFA, invoice, track, contact… |
| `docs/FIZETES.md` | Demo / Stripe / SimplePay |
| `docs/KEPEK.md` | Feltöltés + CDN base |
| `docs/WEBHOOKOK.md` | Outbound |
| `docs/PROD.md` / `docs/DEPLOY.md` | Élesítés |
| `docs/WHOOPY_ERP_INTEGRATION.md` | ERP kötés |
| ERP `Documentation/ai/WHOOPY_SYNC.md` | ERP sync részletek |

---

## 5. Környezet / indítás

```bash
cd "C:\Users\korom\Személyes\taxonomy-marketplace"
.\.venv\Scripts\activate
python run.py
# vagy: docker compose up --build
```

ERP: külön venv, `:8010`. Whoopy `.env` ↔ ERP `.env` **ugyanaz** az `API_KEY` / `WHOOPY_API_KEY` és webhook secret.

---

## 6. Kész roadmap (1–8) + további lépések állapota

1. ERP → Whoopy kliens ✅  
2. Fizetés ✅ (+ SimplePay IPN signature, sandbox flag)  
3. Képek ✅ (+ `MEDIA_PUBLIC_BASE` CDN)  
4. Webhook ✅  
5. Admin Shopify-szint ✅  
6. Merchant Center ✅  
7. Prod hardening ✅ (+ Dockerfile / compose)  
8. Belső partner ops ✅  
9. **ERP master autosync** ✅ (`WHOOPY_AUTOSYNC_*`, `/whoopy-sync/autosync`)  
10. **CDN media base** ✅  
11. **SimplePay sandbox hardening** ✅  
12. **Deploy docs + Docker** ✅  
13. **whoopy_orders + presence + S3 + smoke** ✅  
14. **EU webshop csomag** ✅ (`docs/EU_SHOP.md`)  

### Érdemes következő iterációk

1. SimplePay éles merchant + nyilvános IPN URL (üzleti / DNS)  
2. Domain DNS + TLS (Caddy/Cloudflare) a `docs/DEPLOY.md` szerint  
3. Checkout E2E bővítés + NAV e-számla

### Kerüld el

- Supplier portal / partner self-listing UI  
- Whoopy → ERP katalógus **pull** (felesleges; ERP pushol)  
- Schema wipe productionben  
- Jira/Confluence írás user jóváhagyás nélkül (workspace rule)  

---

## 7. Hogyan folytasd (checklist új AI-nak)

1. Olvasd: `AI_HANDOVER.md` → `docs/AI_SYSTEM.md` → `docs/PARTNEREK.md`  
2. Indítsd Whoopy-t, nézd `/admin/integrations`  
3. Ha ERP-t nyúlsz: `WHOOPY_ENABLED=true`, teszteld `POST /whoopy-sync/autosync`  
4. Schema: növeld `SCHEMA_VERSION` bootstrapban ha modell változik; dev-en `.schema_version` visszaállítható wipe-hoz  
5. Commit üzenet: „miért”, ne „mi”; Whoopy és ERP **külön** GitHub repo  
6. Ne commitolj `.env`, `*.db`, `data/uploads`  

---

## 8. Kapcsolódó path-ek

- Whoopy: `C:\Users\korom\Személyes\taxonomy-marketplace`  
- ERP: `C:\Users\korom\Személyes\e_commerce_erp`  
- Nokia workspace (`ngNCOM`) **nem** része a Whoopy-nak — csak Cursor chat történelem.  
