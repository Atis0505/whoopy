# Google Merchant Center (élesítés)

## Feed URL

```
http://127.0.0.1:8090/feeds/google-merchant.xml
```

Élesben: `https://whoopy.hu/feeds/google-merchant.xml` (állítsd a `PUBLIC_BASE_URL`-t).

## Mit tartalmaz a feed?

- `g:google_product_category` → **taxonomy ID** (szám)
- `g:product_type` → teljes path
- `g:price` / opcionális `g:sale_price` (akció)
- `g:image_link` + `additional_image_link`
- `g:gtin` / `g:mpn` / `identifier_exists`
- Kikapcsolható: Admin → Beállítások → Google Merchant feed

## Validáció

Admin: **Merchant Center** (`/admin/merchant`)  
API: `GET /api/v1/merchant/feed-report` (X-API-Key)

Hibák (nem kerülnek a feedbe): pl. hiányzó kategória, üres cím.  
Figyelmeztetések: pl. nincs kép, nincs GTIN.

## Taxonomy import

1. Admin → Merchant Center → **Taxonomy import** (letöltés pipa)
2. Vagy API: `POST /api/v1/merchant/import-taxonomy?download=true`

Hivatalos forrás:  
https://www.google.com/basepages/producttype/taxonomy-with-ids.en-US.txt  

Cache: `data/taxonomy/taxonomy-with-ids.en-US.txt` (gitben nincs).

Ha nincs hálózat: a seed **curated** részhalmazt használ.

## GMC checklist

1. Google Merchant Center fiók + whoopy.hu domain verify
2. Feed hozzáadása (scheduled fetch)
3. `PUBLIC_BASE_URL` = éles HTTPS URL
4. Termékek: kategória + kép + (lehetőleg) GTIN
5. Admin report: 0 error, included > 0

## CMS megjegyzés

Információs oldalak: `/pages/{slug}` (nem `/p/…` — az a termékoldal).
