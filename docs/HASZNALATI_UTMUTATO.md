# Whoopy.hu – Használati útmutató (magyar)

Ez a dokumentum a **bolt (vásárlói UI)**, az **admin / dolgozó felület** és a **Management API** használatát írja le.

| Rendszer | URL |
|----------|-----|
| Bolt | http://127.0.0.1:8090 |
| Admin | http://127.0.0.1:8090/admin |
| API Swagger | http://127.0.0.1:8090/docs |
| GitHub | https://github.com/Atis0505/whoopy |

Indítás:

```bash
cd "C:\Users\korom\Személyes\taxonomy-marketplace"
.\.venv\Scripts\activate
python run.py
```

---

## 1. Vásárlói felület (bolt)

### 1.1 Főoldal (`/`)

- Kampánycsíkok / hero (adminban szerkeszthető)
- Kiemelt / legtöbbet rendelt termékek
- Kategória belépők (Google Taxonomy fa)
- Nyelv és valuta váltó a fejlécben

### 1.2 Böngészés

| Oldal | Mit csinál |
|-------|------------|
| `/taxonomy` | Teljes kategóriafa |
| `/c/{id}` | Kategória terméklista |
| `/p/{slug}` | Termékoldal – több beszállítói ajánlat (ár, készlet, szállítási nap) |

A termékoldalon válaszd ki a kívánt **ajánlatot** (beszállító), majd add a kosárhoz.

### 1.3 Kosár és fizetés

1. **Kosár** (`/cart`): mennyiség, kupon, ország, fizetési preferencia (előre / utánvét / számla).
2. Több beszállító esetén **több szállítmány** jelenik meg – szállítási mód szállítmányonként választható.
3. **Checkout** (`/checkout`): szállítási adatok → rendelés leadása.
4. **Rendelés visszaigazolás** (`/order/{szám}`): tételek + szállítmányok.

**Tippek**

- `combinable` termékek egy csomagba mehetnek; `separate` (pl. bútor) darabonként számol szállítást.
- Kuponpéldák (seed): `WELCOME10`, `SAVE2000`, `FREESHIP`.

### 1.4 Fiók

| Művelet | Útvonal |
|---------|---------|
| Regisztráció | `/register` |
| Belépés | `/login` |
| Saját fiók / rendelések | `/account` |
| Hírlevél | lábléc űrlap |

**Demo vásárló:** `vasarlo@whoopy.local` / `vasarlo123`

### 1.5 Nyelv és valuta

A fejlécben váltható (többek között): `hu`, `en`, `de`, `pl`, `ro` · `HUF`, `EUR`, …  
Az árak a boltban HUF-ból váltódnak; a katalógus tárolása HUF.

### 1.6 Google Merchant feed

`GET /feeds/google-merchant.xml` — Google Merchant Center / Shopping feed (taxonomy path-okkal).

---

## 2. Admin és dolgozó felület

Belépés: **`/login`** (ugyanaz a belépő, szerepkör dönti el a jogosultságot).

| Szerep | Demo fiók | Jelszó | Hová kerül |
|--------|-----------|--------|------------|
| Admin | `admin@whoopy.local` | `admin1234` | `/admin` – teljes menü |
| Dolgozó | `dolgozo@whoopy.local` | `worker123` | `/admin/orders` – rendelés / készlet |
| Vásárló | `vasarlo@whoopy.local` | `vasarlo123` | `/account` |

### 2.1 Admin menü (összefoglaló)

| Menü | Cél |
|------|-----|
| **Dashboard** | Áttekintés |
| **Rendelések** | Lista, státusz, szállítmány / tracking |
| **Termékek** | Katalógus áttekintés |
| **Beszállítók** | Supplier kódok (API-hoz is kell) |
| **Szállítás** | Ország / mód / COD díjak |
| **Kedvezmények** | Kuponok |
| **Termékakciók** | Százalékos / fix akciók |
| **Kampányok** | Főoldali hero / strip / tile |
| **Hírlevél** | Feliratkozók |
| **Integrációk** | ERP / API állapot (őszinte státusz) |

> Megjegyzés: a sidebarban megjelenő néhány menüpont (analitika, CMS, settings…) részben még fejlesztés alatt lehet — a fenti tábla a ténylegesen használt mag.

### 2.2 Tipikus admin feladatok

1. **Új kampány:** Kampányok → cím, badge, kép URL, link, placement (`hero` / `strip` / `tile`).
2. **Kupon:** Kedvezmények → kód, típus (`percent` / `fixed` / `free_shipping`), minimum kosár.
3. **Rendelés feldolgozás:** Rendelések → státusz (`pending` → `paid` → `fulfilled`), tracking a szállítmányon.
4. **Beszállító:** kód (pl. `HU-BUD-01`) legyen stabil — az API `supplier_code` ezzel egyezik.

### 2.3 Dolgozó

Csak rendelés- és készletkezelés; marketing / beszállító / kampány menük nem jelennek meg.

---

## 3. Management API (rövid)

Részletes referencia: [`API.md`](API.md) · Swagger: `/docs`

**Auth:** minden hívásnál

```http
X-API-Key: whoopy-dev-api-key-change-me
```

(Élesben állítsd át: env `API_KEY`.)

### Leggyakoribb műveletek

| Cél | Metódus + útvonal |
|-----|-------------------|
| Termék létrehozás | `POST /api/v1/products` |
| Create vagy frissítés (ERP) | `PUT /api/v1/products/upsert` |
| Ármódosítás | `PATCH /api/v1/offers/{id}/price` |
| Készlet | `PATCH /api/v1/offers/{id}/stock` |
| Tömeges ár/készlet | `POST /api/v1/offers/bulk-price` |
| Rendelések | `GET /api/v1/orders` |
| Státusz | `PATCH /api/v1/orders/{id}/status` |

**ERP oldal:** az `e_commerce_erp` Whoopy adaptere ezeket hívja (`WHOOPY_API_URL`, `WHOOPY_API_KEY`).  
Lásd: ERP `Documentation/ai/WHOOPY_SYNC.md` (ha telepítve) és [`WHOOPY_ERP_INTEGRATION.md`](WHOOPY_ERP_INTEGRATION.md).

---

## 4. Gyakori kérdések

**Miért több szállítási sor a kosárban?**  
Különböző beszállítók külön csomagot indítanak.

**Hol állítsam az API kulcsot?**  
Whoopy: `app/config.py` / `API_KEY`. ERP: `.env` → `WHOOPY_API_KEY` (ugyanaz az érték).

**A DB újraseedelődik?**  
Ha a `.schema_version` változik, fejlesztői módban a SQLite újraépülhet — ne tárolj éles adatot a helyi `marketplace.db`-ben.

**Hol a GitHub?**  
https://github.com/Atis0505/whoopy
