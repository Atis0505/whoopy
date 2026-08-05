# Admin (Shopify-szerű) – magyar használati útmutató

Belépés: http://127.0.0.1:8090/login  
Demo admin: `admin@whoopy.local` / `admin1234`  
Demo dolgozó: `dolgozo@whoopy.local` / `worker123`

## Menü

| Menü | Útvonal | Mit csinál |
|------|---------|------------|
| Dashboard | `/admin` | Darabszámok + legutóbbi rendelések |
| Analitika | `/admin/analytics` | 30 nap forgalom, 7 nap trend, top termékek |
| Rendelések | `/admin/orders` | Lista + státusz |
| Vásárlók | `/admin/customers` | Customer role fiókok |
| Elhagyott kosarak | `/admin/abandoned-carts` | 2 óránál régebbi nem üres kosarak |
| Termékek | `/admin/products` | Katalógus + képfeltöltés |
| Készlet | `/admin/inventory` | Offer stock szerkesztés, low-stock |
| Kategóriák | `/admin/categories` | Google taxonomy kereső |
| Beszállítók | `/admin/suppliers` | Supplier kódok |
| Kedvezmények / akciók / kampányok / hírlevél | … | Marketing |
| Oldalak (CMS) | `/admin/pages` | ÁSZF, adatvédelem… → bolt `/p/{slug}` |
| Szállítás | `/admin/shipping` | Rate-ek |
| Integrációk | `/admin/integrations` | Őszinte ERP / fizetés / webhook státusz |
| Webhook-ek | `/admin/webhooks` | Outbound célok + delivery log |
| Beállítások | `/admin/settings` | Bolt név, ÁFA, low-stock, maintenance |
| Személyzet | `/admin/staff` | Admin / worker létrehozás |

## Bolt CMS

Publikált oldalak: `/p/aszf`, `/p/adatvedelem`, `/p/rolunk` (seed).

## Megjegyzés

Ez **nem** teljes Shopify parity (nincs themes editor, app store, POS) — a bolt backoffice magja van meg, amit a sidebar ígér.
