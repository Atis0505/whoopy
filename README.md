# Whoopy.hu – Storefront

**Domain:** whoopy.hu  
**GitHub:** https://github.com/Atis0505/whoopy  
**Lokális:** http://127.0.0.1:8090  
**Projekt:** `C:\Users\korom\Személyes\taxonomy-marketplace`  
**Schema:** v13

Alza / eMAG / Pepita jellegű, **Google Taxonomy** alapú, többbeszállítós marketplace webshop.  
ERP: `e_commerce_erp` — `docs/WHOOPY_ERP_INTEGRATION.md`.

> **AI:** [`AI_HANDOVER.md`](AI_HANDOVER.md) · [`docs/AI_SYSTEM.md`](docs/AI_SYSTEM.md)  
> **Használat:** [`docs/HASZNALATI_UTMUTATO.md`](docs/HASZNALATI_UTMUTATO.md) · Admin: [`docs/ADMIN.md`](docs/ADMIN.md) · Terv: [`docs/FEJLESZTESI_TERV.md`](docs/FEJLESZTESI_TERV.md)

## Indítás

```bash
cd "C:\Users\korom\Személyes\taxonomy-marketplace"
.\.venv\Scripts\activate
python run.py
```

- Bolt: http://127.0.0.1:8090  
- Admin: http://127.0.0.1:8090/admin (`admin@whoopy.local` / `admin1234`)  
- API: http://127.0.0.1:8090/docs (`X-API-Key`)  
- Smoke: `python -m pytest tests/test_smoke.py -q`

## Képességek (rövid)

- Több beszállító / ajánlat, kupon, akció, hírlevél, regisztráció
- EU ország + valuta + több nyelv · B2B reverse charge · Omnibus ár
- Csomaglogisztika (combinable/separate), csomagpont stub, futár/RMA stub, multi-warehouse
- Feedek: Google Merchant, Meta, Árukereső · UTM / affiliate · hero A/B
- Management API `/api/v1` · fizetés (demo/Stripe/SimplePay) · Számlázz stub
- Webhook → ERP · partner staging/feed/árazás/beszerzés (nincs supplier portal)
- GDPR: cookie CMP, adat-export, fiók-anonimizálás

Részletek: `docs/UX.md`, `docs/MARKETING.md`, `docs/LOGISTICS_COMPLIANCE.md`, `docs/EU_SHOP.md`.

## ERP

`C:\Users\korom\Személyes\e_commerce_erp` (8010/5181) · `docs/WHOOPY_ERP_INTEGRATION.md`, `docs/API.md`.
