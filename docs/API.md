# Whoopy Management API (`/api/v1`)

REST API az ERP-hez és automatizációhoz: termékfeltöltés, ármódosítás, készlet, rendelések.

## Auth

Minden endpoint (kivéve a storefront HTML) az alábbi headert várja:

```http
X-API-Key: whoopy-dev-api-key-change-me
```

A kulcs: `app/config.py` → `api_key` (vagy env: `API_KEY`).

Interaktív docs: [http://127.0.0.1:8090/docs](http://127.0.0.1:8090/docs) (Authorize → API key).

## Gyors példák

### Termék feltöltés ajánlattal

```bash
curl -s -X POST http://127.0.0.1:8090/api/v1/products \
  -H "X-API-Key: whoopy-dev-api-key-change-me" \
  -H "Content-Type: application/json" \
  -d "{
    \"slug\": \"demo-kulacs-500\",
    \"title\": \"Whoopy kulacs 500ml\",
    \"brand\": \"Whoopy\",
    \"gtin\": \"5990000000001\",
    \"weight_kg\": 0.4,
    \"ship_mode\": \"combinable\",
    \"google_taxonomy_id\": 111,
    \"offers\": [{
      \"supplier_code\": \"HU-BUD-01\",
      \"sku\": \"BUD-KULACS-500\",
      \"price\": 2990,
      \"stock\": 40,
      \"lead_days\": 2
    }]
  }"
```

### Upsert (ERP szinkron — create vagy update slug/gtin alapján)

```bash
curl -s -X PUT http://127.0.0.1:8090/api/v1/products/upsert \
  -H "X-API-Key: whoopy-dev-api-key-change-me" \
  -H "Content-Type: application/json" \
  -d "{
    \"match_by\": \"gtin\",
    \"slug\": \"demo-kulacs-500\",
    \"title\": \"Whoopy kulacs 500ml (frissített)\",
    \"gtin\": \"5990000000001\",
    \"offers\": [{
      \"supplier_code\": \"HU-BUD-01\",
      \"sku\": \"BUD-KULACS-500\",
      \"price\": 2790,
      \"stock\": 55
    }]
  }"
```

### Ármódosítás meghirdetett ajánlaton

```bash
curl -s -X PATCH http://127.0.0.1:8090/api/v1/offers/1/price \
  -H "X-API-Key: whoopy-dev-api-key-change-me" \
  -H "Content-Type: application/json" \
  -d "{\"price\": 2490}"
```

### Tömeges ár / készlet

```bash
curl -s -X POST http://127.0.0.1:8090/api/v1/offers/bulk-price \
  -H "X-API-Key: whoopy-dev-api-key-change-me" \
  -H "Content-Type: application/json" \
  -d "{
    \"items\": [
      {\"sku\": \"BUD-KULACS-500\", \"price\": 2490, \"stock\": 60},
      {\"product_slug\": \"demo-kulacs-500\", \"supplier_code\": \"HU-BUD-01\", \"price\": 2490}
    ]
  }"
```

### Készlet

```bash
curl -s -X PATCH http://127.0.0.1:8090/api/v1/offers/1/stock \
  -H "X-API-Key: whoopy-dev-api-key-change-me" \
  -H "Content-Type: application/json" \
  -d "{\"stock\": 12}"
```

### Rendelések

```bash
curl -s "http://127.0.0.1:8090/api/v1/orders?status=pending" \
  -H "X-API-Key: whoopy-dev-api-key-change-me"

curl -s -X PATCH http://127.0.0.1:8090/api/v1/orders/1/status \
  -H "X-API-Key: whoopy-dev-api-key-change-me" \
  -H "Content-Type: application/json" \
  -d "{\"status\": \"paid\"}"
```

## Endpoint összefoglaló

| Terület | Metódus | Útvonal | Leírás |
|---------|---------|---------|--------|
| Meta | GET | `/api/v1/health` | Állapot |
| Catalog | GET | `/api/v1/categories` | Google taxonomy kategóriák |
| Catalog | GET/POST | `/api/v1/suppliers` | Beszállítók |
| Products | GET/POST | `/api/v1/products` | Lista / létrehozás |
| Products | PUT | `/api/v1/products/upsert` | Create-or-update |
| Products | GET/PATCH/DELETE | `/api/v1/products/{id}` | Részletek / módosítás / soft-delete |
| Products | GET | `/api/v1/products/by-slug/{slug}` | Slug alapján |
| Offers | GET | `/api/v1/offers` | Ajánlatok listája |
| Offers | POST | `/api/v1/products/{id}/offers` | Új ajánlat |
| Offers | PATCH | `/api/v1/offers/{id}` | Teljes patch |
| Offers | PATCH | `/api/v1/offers/{id}/price` | Gyors ár |
| Offers | PATCH | `/api/v1/offers/{id}/stock` | Gyors készlet |
| Offers | POST | `/api/v1/offers/bulk-price` | Tömeges ár/készlet |
| Offers | DELETE | `/api/v1/offers/{id}` | Soft-delete |
| Orders | GET | `/api/v1/orders` | Rendelések |
| Orders | GET | `/api/v1/orders/{id}` | Rendelés |
| Orders | GET | `/api/v1/orders/by-number/{n}` | Rendelésszám |
| Orders | PATCH | `/api/v1/orders/{id}/status` | Státusz |
| Orders | PATCH | `/api/v1/shipments/{id}` | Tracking / státusz |
| Marketing | GET/POST | `/api/v1/campaigns` | Kampányok |
| Marketing | GET/POST | `/api/v1/coupons` | Kuponok |
| Media | GET/POST | `/api/v1/products/{id}/images` | Képlista / feltöltés |
| Media | POST | `/api/v1/products/{id}/images/{img}/primary` | Elsődleges kép |
| Media | DELETE | `/api/v1/products/{id}/images/{img}` | Kép törlés |

Részletes képfeltöltés: [`KEPEK.md`](KEPEK.md)


## ERP státusz

Az API **Whoopy oldalon kész**. Az `e_commerce_erp` bridge (`erp_enabled`) továbbra is **kikapcsolva** — az ERP-nek ezt az API-t kell hívnia (push), vagy később bidirectional sync.

Részletek: `docs/WHOOPY_ERP_INTEGRATION.md`
