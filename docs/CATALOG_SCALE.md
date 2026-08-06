# Katalógus skálázás — schema v16

Cél: **40–80k SKU** előtt a listák ne töltsék be az egész katalógust memóriába.

## Pagination

| Felület | Oldalméret | Hol |
|---------|------------|-----|
| Főoldal / szűrők | 48 | `services/catalog.py` · `/` |
| Kategória | 48 | `/c/{google_id}` |
| Keresés | 48 | `/search` |
| Admin termékek / rendelések / készlet | 50 | `/admin/products` · `orders` · `inventory` |

Ár / készlet szűrés SQL-ben (min offer subquery), nem Python-ban az összes termékre.

## Indexek

SQLite / Postgres: `products(brand, gtin, sold_count, category_id, active)`, `products(active, created_at)`, `offers(active, stock)`.

Bootstrap v16: `CREATE INDEX IF NOT EXISTS …` wipe nélkül.

## Sitemap

- ≤ 5000 aktív termék → egy `/sitemap.xml` urlset
- felette → sitemap index + `/sitemap/{n}.xml` chunkok (`SITEMAP_CHUNK=5000`)

## Megjegyzés

Promo-kalkulált „display” ár a listán még a betöltött oldal enrich lépésében van; a szűrés/rendezés a listaár (`Offer.price`) alapján történik. Nagy katalógusnál Postgres + CDN media ajánlott (`docs/PROD.md`).
