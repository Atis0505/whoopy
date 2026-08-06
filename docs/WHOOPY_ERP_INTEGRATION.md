# Whoopy.hu ↔ e_commerce_erp integráció

## Cél

| Rendszer | Szerep |
|----------|--------|
| **Whoopy** (`taxonomy-marketplace`, :8090) | Vevői webshop: whoopy.hu, kosár, checkout, Merchant feed |
| **ERP** (`e_commerce_erp`, API :8010 / UI :5181) | Katalógus agy: partnerek, feed, staging→master, ár, Pepita, szállítás |

## Aktuális irány (2026)

| Irány | Állapot |
|-------|---------|
| **ERP → Whoopy** katalógus | ✅ Management API + `whoopy-sync` push + **autosync** |
| **Whoopy → ERP** rendelés | ✅ Outbound webhook + ERP poll `GET /orders`; inbox JSONL |
| Whoopy katalógus pull ERP-ből | ❌ Nem kell — ERP pushol |

Részletek: ERP `Documentation/ai/WHOOPY_SYNC.md` · Whoopy `docs/AI_SYSTEM.md`

### Env

**Whoopy:** `API_KEY`, `WEBHOOK_*`, opcionálisan `ERP_ENABLED` + `ERP_API_BASE` (admin autosync gomb).  
**ERP:** `WHOOPY_ENABLED`, `WHOOPY_API_URL`, `WHOOPY_API_KEY`, `WHOOPY_AUTOSYNC_*`, `WHOOPY_WEBHOOK_SECRET`.

### Tervezett ERP táblák (később)

`whoopy_listings`, `whoopy_offers`, `whoopy_orders`, … — a webhook egyelőre `data/whoopy_webhook_inbox.jsonl`.

## Google Taxonomy / Merchant

Feed: `GET /feeds/google-merchant.xml` — lásd `docs/MERCHANT.md`.

## Csomag / EU logisztika (Whoopy)

- Több beszállító egy kosárban → több szállítmány  
- `combinable` vs `separate`  
- Admin beszerzés: `/admin/procurement`
