# Whoopy.hu ↔ e_commerce_erp integráció

## Cél

| Rendszer | Szerep |
|----------|--------|
| **Whoopy** (`taxonomy-marketplace`, :8090) | Vevői webshop: whoopy.hu, kosár, checkout, Merchant feed |
| **ERP** (`e_commerce_erp`, API :8010 / UI :5181) | Katalógus agy: partnerek, feed, staging→master, ár, Pepita, szállítás |

Whoopy **saját sales channel** lesz az ERP-ben (mint a Pepita marketplace), saját táblákkal.

## Miért Google Taxonomy?

A termékek `google_product_category` / taxonomy path mezője kell a **Google Merchant Center** feedhez.
Ha a kategória jól van kötve, a Google Shopping / keresés fel tudja ajánlani a Whoopy termékeket.
Feed most: `GET /feeds/google-merchant.xml`

## Tervezett ERP táblák (Whoopy channel)

| Tábla | Tartalom |
|-------|----------|
| `whoopy_listings` | master product → Whoopy slug, active, taxonomy id |
| `whoopy_offers` | partner/supplier ár+készlet mirror |
| `whoopy_orders` | whoopy.hu rendelés header |
| `whoopy_order_lines` | tételek |
| `whoopy_order_shipments` | csomag / beszállító lábak (EU) |
| `whoopy_sync_cursor` | utolsó sync időbélyeg |

Kód stub: `app/services/erp_bridge.py` (`erp_enabled`, `erp_api_base`).

## Szinkron irányok (később)

1. **ERP → Whoopy:** jóváhagyott master + offer pull (taxonomy + kép + ár)
2. **Whoopy → ERP:** rendelés push (split shipments, fizetési mód, ország)
3. **Közös:** exchange rates, shipping bindings mintái az ERP `shipping_*` / partner shipping configból

## Csomag / EU logisztika (Whoopy oldalon már)

- Több beszállító egy kosárban → több szállítmány
- `combinable` vs `separate` (pl. 2 szekrény = 2 csomagdíj)
- prepaid / COD / invoice opciók országonként
- Több EU célország

## Kapcsolódó ERP területek

- Partnerek + feed: `Documentation/ai/knowledge-base/02-partners-feeds.md`
- Marketplace listings / prep API
- `ShippingProvider`, `PartnerShippingConfig`, `MarketplaceShippingMethod`
- Category mappings (Google / Pepita taxonomy)

## Whoopy Management API (kész)

Az ERP (vagy bármely kliens) **pusholhat** Whoopy-ra:

- termék create / upsert
- ár + készlet (egyedi és bulk)
- rendelés státusz / tracking olvasás

Dokumentáció: [`docs/API.md`](API.md) · Használat: [`HASZNALATI_UTMUTATO.md`](HASZNALATI_UTMUTATO.md) · Swagger: `http://127.0.0.1:8090/docs`  
Auth: `X-API-Key` (`API_KEY` / `settings.api_key`).

**ERP kliens (kész):** `e_commerce_erp` → `/api/v1/whoopy-sync/*` · leírás: ERP `Documentation/ai/WHOOPY_SYNC.md`

## Bekapcsolás (ERP → Whoopy)

```env
# Whoopy
API_KEY=whoopy-dev-api-key-change-me

# ERP .env
WHOOPY_ENABLED=true
WHOOPY_API_BASE=http://127.0.0.1:8010/api/v1
WHOOPY_API_URL=http://127.0.0.1:8090/api/v1
WHOOPY_API_KEY=whoopy-dev-api-key-change-me
```

Whoopy önálló SQLite katalógussal fut; az ERP a fenti sync API-n tolja a listingeket.

