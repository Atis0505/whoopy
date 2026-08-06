# AI Handover – Whoopy.hu

> Olvasd el session elején. **Teljes rendszerkép:** [`docs/AI_SYSTEM.md`](docs/AI_SYSTEM.md)

## Mi ez?

**Whoopy.hu** storefront – Google Taxonomy marketplace (Alza/eMAG/Pepita jellegű UI).  
- **GitHub:** https://github.com/Atis0505/whoopy  
- **Helyi útvonal:** `C:\Users\korom\Személyes\taxonomy-marketplace`  
- **Port:** **8090** (nem 8000)

Kapcsolódó ERP: `C:\Users\korom\Személyes\e_commerce_erp` (:8010 / :5181)  
Integráció: `docs/WHOOPY_ERP_INTEGRATION.md` · API: `docs/API.md` · **AI rendszerleírás:** `docs/AI_SYSTEM.md`

## Gyors indítás

```bash
cd "C:\Users\korom\Személyes\taxonomy-marketplace"
.\.venv\Scripts\activate
python run.py
```

Docker: `docker compose up --build` — lásd `docs/DEPLOY.md`.

## Szerepkörök

| Szerep | Belépés | Hová kerül |
|--------|---------|------------|
| **customer** | `/login` vagy regisztráció | `/account` vásárlói nézet |
| **worker** | `/login` | `/admin/orders` (+ partners / procurement) |
| **admin** | `/login` | `/admin` teljes admin |

Demo: `vasarlo@whoopy.local` / vasarlo123 · `dolgozo@whoopy.local` / worker123 · `admin@whoopy.local` / admin1234

## Partner modell (fontos)

- Partnerek = források, ahonnan Whoopy vásárol — nem self-listing eladók  
- Admin: `/admin/partners`, `/admin/staging`, `/admin/feeds`, `/admin/procurement`, …  
- Schema **v8** · Doc: `docs/PARTNEREK.md`

## ERP

- Push: ERP `/api/v1/whoopy-sync/*` + **autosync** (`WHOOPY_AUTOSYNC_ENABLED`)  
- Whoopy admin: Integrációk → ERP autosync gomb (`ERP_ENABLED=true`)  
- Webhook: Whoopy → ERP `POST /webhooks/whoopy` → JSONL inbox  

## Roadmap

Lásd `docs/FEJLESZTESI_TERV.md` — 1–12 kész.  
Következő opcionális: whoopy_orders pipeline, S3/R2, éles SimplePay merchant, E2E.
