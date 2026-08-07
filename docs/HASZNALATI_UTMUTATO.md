# Whoopy.hu – Használati útmutató (magyar)

Ez a dokumentum a **bolt (vásárlói UI)**, az **admin / dolgozó felület** és a **Management API** használatát írja le.  
Schema: **v16** · GitHub: https://github.com/Atis0505/whoopy

| Rendszer | URL |
|----------|-----|
| Bolt | http://127.0.0.1:8090 |
| Admin | http://127.0.0.1:8090/admin |
| API Swagger | http://127.0.0.1:8090/docs |

Indítás:

```bash
cd "C:\Users\korom\Személyes\taxonomy-marketplace"
.\.venv\Scripts\activate
python run.py
```

További vásárlói / ops funkciók: felső hirdetőszalag, social ticker, bolt zárás — lásd [`STOREFRONT_OPS.md`](STOREFRONT_OPS.md).  
Ártörténet / ismétlődő rendelés: [`OMNIBUS_SUBSCRIPTIONS.md`](OMNIBUS_SUBSCRIPTIONS.md).  
Nagy katalógus (lapozás): [`CATALOG_SCALE.md`](CATALOG_SCALE.md).

---

## 1. Vásárlói felület (bolt)

### 1.1 Főoldal (`/`)

- Kampány hero / strip / tile (A/B csoporttal)
- Kiemelt / legtöbbet rendelt termékek
- Kategória belépők (Google Taxonomy)
- Nyelv és valuta a fejlécben
- Cookie CMP banner (szükséges / analitika / marketing)

### 1.2 Böngészés és keresés

| Oldal | Mit csinál |
|-------|------------|
| `/` + keresőmező | Élő javaslatok (`/api/suggest`); terméklista **lapozva** (48/oldal), márka/ár/készlet szűrő |
| `/search?q=` | Találati lista (lapozva) |
| `/taxonomy` | Teljes kategóriafa |
| `/c/{id}` | Kategória terméklista (lapozva) |
| `/account` | Fiók: rendelések, **ismétlődő újrarendelés**, GDPR export/törlés, hírlevél |
| `/p/{slug}` | Termék: ajánlatok, variáns, **Omnibus 30 nap** legalacsonyabb ár, vélemények |
| `/compare` | Összehasonlítás |
| `/recent` | Nemrég nézett |
| `/wishlist` | Kívánságlista |

A termékoldalon válaszd az **ajánlatot** (beszállító / variáns), majd kosár.  
Ismétlés: kosárból vagy a fiókban egy korábbi rendelésnél „Ismétlés” (7–90 nap).

További oldalak: `/contact`, `/faq`, `/track`, `/returns`, jogi CMS (`/pages/…` — ÁSZF, adatvédelem, sütik, impresszum, szállítás, elállás, rólunk). Részletek: [`LEGAL.md`](LEGAL.md).

### 1.3 Kosár és checkout

1. **Kosár** (`/cart`): mennyiség, kupon, ajándékutalvány, hűségpont, fizetési mód, **futár vs csomagpont**, **B2B adószám**.
2. Több beszállító → több szállítmány; szállítási mód szállítmányonként.
3. **Checkout** (`/checkout`): szállítási + opcionális eltérő számlázási cím → rendelés.
4. Előre fizetésnél → `/pay/...` ([`FIZETES.md`](FIZETES.md)).
5. **Rendelés** (`/order/{szám}`): tételek, szállítmányok, HTML számla link.

**Tippek**

- Kuponok (seed): `WELCOME10`, `SAVE2000`, `FREESHIP`.
- Ajándékutalvány (seed): `WHOOPY5K`.
- B2B: pipáld a kosárban, add meg az EU adószámot (pl. `DE123456789`) → más EU ország esetén reverse charge (ÁFA 0%).
- Csomagpont: Foxpost / Packeta / GLS stub lista.

### 1.4 Fiók és GDPR

| Művelet | Útvonal |
|---------|---------|
| Regisztráció / belépés | `/register`, `/login` |
| Fiók / rendelések | `/account` |
| Adatok exportja (JSON) | `/account/export` |
| Fiók törlése | `/account/delete` — confirm mező: `TORLES` |
| Hírlevél | lábléc vagy fiók |

**Demo vásárló:** `vasarlo@whoopy.local` / `vasarlo123`

### 1.5 Nyelv, valuta, feedek

Nyelvek: `hu`, `en`, `de`, … · Valuták: `HUF`, `EUR`, …  
Feedek: Google Merchant, Meta katalog, Árukereső — lásd [`MARKETING.md`](MARKETING.md).

---

## 2. Admin és dolgozó

Belépés: **`/login`**.

| Szerep | Demo | Jelszó | Hová |
|--------|------|--------|------|
| Admin | `admin@whoopy.local` | `admin1234` | `/admin` |
| Dolgozó | `dolgozo@whoopy.local` | `worker123` | `/admin/orders` |
| Vásárló | `vasarlo@whoopy.local` | `vasarlo123` | `/account` |

### 2.1 Fontos menüpontok

| Menü | Cél |
|------|-----|
| **Rendelések** | Státusz, futár **címke**, tracking sync, partial fulfill, Számlázz dry-run |
| **Ismétlődő rendelések** | Due runner / manuális futtatás (`/admin/subscriptions`) |
| **Visszaküldések** | RMA címke + refund |
| **Raktárak** | Multi-warehouse (`BUD-01` default) |
| **Ártörténet** | Omnibus PriceHistory riporter (`/admin/price-history`) |
| **Készlet** | Stock + ár (árváltozás naplózva) |
| **Marketing** | Feed URL-ek, UTM, affiliate, A/B |
| **Partnerek / Staging / Feed / Beszerzés…** | Belső ops — [`PARTNEREK.md`](PARTNEREK.md) |
| **Integrációk / Webhook-ek** | ERP, fizetés állapot |

Részletes menü: [`ADMIN.md`](ADMIN.md).

### 2.2 Tipikus folyamatok

1. **Rendelés kiszállítás:** Rendelések → szállítmány → Címke (GLS/Foxpost/…) → Tracking sync → státusz `shipped` / `delivered`. Több csomag külön kezelhető (`partial` → `fulfilled`).
2. **Visszaküldés:** Vásárló `/returns` → admin RMA címke → Refund.
3. **Partner áru:** Feed CSV → Staging → Publish.
4. **Kampány:** Kampányok + Marketing A/B.

### 2.3 Dolgozó

Rendelés, visszaküldés, készlet, partnerek, beszerzés — marketing / settings / staff nem.

---

## 3. Management API (rövid)

[`API.md`](API.md) · Swagger: `/docs`

```http
X-API-Key: whoopy-dev-api-key-change-me
```

| Cél | Metódus |
|-----|---------|
| Termék upsert | `PUT /api/v1/products/upsert` |
| Ár / készlet | `PATCH /api/v1/offers/{id}/price` · `…/stock` |
| Rendelések | `GET /api/v1/orders` |

ERP: `e_commerce_erp` Whoopy adapter (`WHOOPY_API_URL`, `WHOOPY_API_KEY`) — [`WHOOPY_ERP_INTEGRATION.md`](WHOOPY_ERP_INTEGRATION.md).

---

## 4. Gyakori kérdések

**Miért több szállítási sor?** Különböző beszállítók külön csomagot indítanak.

**Hol az API kulcs?** Whoopy `API_KEY` · ERP `WHOOPY_API_KEY` (ugyanaz).

**A DB újraseedelődik?** Schema bump (`.schema_version`) → **dev SQLite wipe**. Éles Postgres soha.

**Számla / futár éles?** Stub outbox (`data/szamlazz_outbox`, `data/carrier_outbox`) amíg nincs Agent / futár kulcs.

**Hol a GitHub?** https://github.com/Atis0505/whoopy
