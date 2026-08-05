# AI Handover – Whoopy.hu

> Olvasd el session elején.

## Mi ez?

**Whoopy.hu** storefront – Google Taxonomy marketplace (Alza/eMAG/Pepita jellegű UI).  
- **GitHub:** https://github.com/Atis0505/whoopy  
- **Helyi útvonal:** `C:\Users\korom\Személyes\taxonomy-marketplace`  
- **Port:** **8090** (nem 8000)

Kapcsolódó ERP: `C:\Users\korom\Személyes\e_commerce_erp` (:8010 / :5181)  
Integrációs terv: `docs/WHOOPY_ERP_INTEGRATION.md` · API: `docs/API.md`

## Gyors indítás

```bash
cd "C:\Users\korom\Személyes\taxonomy-marketplace"
.\.venv\Scripts\activate
python run.py
```

## Szerepkörök

| Szerep | Belépés | Hová kerül |
|--------|---------|------------|
| **customer** | `/login` vagy regisztráció | `/account` vásárlói nézet |
| **worker** | `/login` | `/admin/orders` (rendeléskezelés) |
| **admin** | `/login` | `/admin` teljes admin |

Demo: `vasarlo@whoopy.local` / vasarlo123 · `dolgozo@whoopy.local` / worker123 · `admin@whoopy.local` / admin1234

## Merchandising

- **Kampányok** (`Campaign`): hero / strip / tile – admin: `/admin/campaigns`
- **Legtöbben rendelték**: `Product.sold_count` alapján a főoldalon

## Fontos URL-ek

| URL | Szerep |
|-----|--------|
| `/` | Főoldal |
| `/docs` | OpenAPI (Management API) |
| `/api/v1/*` | ERP / automation API (`X-API-Key`) |
| `/feeds/google-merchant.xml` | Google Merchant feed |
| `/admin` | Admin |
| `/cart` | Kosár + multi shipping |

API leírás: `docs/API.md`

## ERP kötés állapota

- `erp_enabled=False` (config) — helyi SQLite katalógus
- **Whoopy Management API kész** (`/api/v1`) — termék upsert, ár/készlet, rendelés
- Stub reverse bridge: `app/services/erp_bridge.py`
- Később: ERP whoopy_* táblák + ERP kliens → Whoopy API push

## Következő lépések

1. ERP-ben Whoopy channel + kliens a Whoopy `/api/v1`-hez
2. Order push / tracking kétirányú
3. Teljes taxonomy import + Merchant Center csatolás
4. Domain / HTTPS whoopy.hu
5. Shopify-szerű admin bővítés (settings, analytics) — opcionális
