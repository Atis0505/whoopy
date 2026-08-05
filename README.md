# Whoopy.hu – Storefront

**Domain:** whoopy.hu  
**GitHub:** https://github.com/Atis0505/whoopy  
**Lokális:** http://127.0.0.1:8090  
**Projekt:** `C:\Users\korom\Személyes\taxonomy-marketplace`

Alza / eMAG / Pepita jellegű, **Google Taxonomy** alapú, többbeszállítós marketplace webshop.
Később az `e_commerce_erp` rendszerhez kapcsolódik (lásd `docs/WHOOPY_ERP_INTEGRATION.md`).

> AI: [`AI_HANDOVER.md`](AI_HANDOVER.md)

## Indítás

```bash
cd "C:\Users\korom\Személyes\taxonomy-marketplace"
.\.venv\Scripts\activate
python run.py
```

- Bolt: http://127.0.0.1:8090  
- Admin: http://127.0.0.1:8090/admin (`admin@whoopy.local` / `admin1234`)  
- API docs: http://127.0.0.1:8090/docs (`X-API-Key`)  
- Google feed: http://127.0.0.1:8090/feeds/google-merchant.xml

## Képességek (rövid)

- Több beszállító / ajánlat, kupon, akció, hírlevél, regisztráció
- EU ország + valuta + 6 nyelv
- Csomaglogisztika: összecsomagolható vs külön (bútor), COD díj
- Merchant Center XML feed taxonomy path-okkal
- **Management API** `/api/v1` — termék, ár, készlet, rendelés (lásd `docs/API.md`)
- ERP reverse-bridge stub (kikapcsolva); ERP → Whoopy push az API-n

## ERP

Saját ERP: `C:\Users\korom\Személyes\e_commerce_erp` (8010/5181).  
Whoopy channel + API: `docs/WHOOPY_ERP_INTEGRATION.md`, `docs/API.md`.
