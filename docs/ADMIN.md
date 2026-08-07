# Admin (Shopify-szerű) – magyar használati útmutató

Belépés: http://127.0.0.1:8090/login  
Demo admin: `admin@whoopy.local` / `admin1234`  
Demo dolgozó: `dolgozo@whoopy.local` / `worker123`

## Menü

| Menü | Útvonal | Mit csinál |
|------|---------|------------|
| Dashboard | `/admin` | Darabszámok + legutóbbi rendelések |
| Analitika | `/admin/analytics` | 30 nap forgalom, trend, top termékek |
| Marketing | `/admin/marketing` | Feed URL-ek, UTM, affiliate, A/B |
| Rendelések | `/admin/orders` | Státusz, futár címke, tracking sync, partial fulfill, Számlázz |
| Visszaküldések | `/admin/returns` | RMA címke + refund |
| Raktárak | `/admin/warehouses` | Multi-warehouse |
| Vásárlók | `/admin/customers` | Customer role fiókok |
| Kapcsolat | `/admin/contact-messages` | Contact űrlap üzenetek |
| Elhagyott kosarak | `/admin/abandoned-carts` | 2 óránál régebbi nem üres kosarak |
| Termékek | `/admin/products` | Katalógus + képfeltöltés |
| Készlet | `/admin/inventory` | Offer stock, low-stock |
| Kategóriák | `/admin/categories` | Google taxonomy kereső |
| Beszállítók | `/admin/suppliers` | Supplier kódok |
| Partnerek / Staging / Feed / Árazás / Beszerzés / Dedup / KPI | `/admin/partners`… | Belső ops — [`PARTNEREK.md`](PARTNEREK.md) |
| Kedvezmények / akciók / kampányok / hírlevél | … | Marketing tartalom |
| Oldalak (CMS) | `/admin/pages` | ÁSZF, adatvédelem… → `/pages/{slug}` |
| Merchant Center | `/admin/merchant` | Feed report + taxonomy import |
| Szállítás | `/admin/shipping` | Rate-ek |
| Integrációk | `/admin/integrations` | ERP / fizetés / webhook státusz |
| Webhook-ek | `/admin/webhooks` | Outbound célok + delivery log |
| Beállítások | `/admin/settings` | Bolt név, ÁFA, low-stock, maintenance |
| Személyzet | `/admin/staff` | Admin / worker létrehozás |

## Bolt CMS

Jogi / tájékoztató oldalak (seed + startup sync, `app/content/legal_pages.py`):
`/pages/aszf`, `adatvedelem`, `sutik`, `impressum`, `szallitas`, `visszakuldes`, `rolunk`.

Cégadatokat (név, cím, adószám, e-mail) a **Beállításokban** töltsd ki — a CMS szövegek `{{company_name}}` stb. placeholdereket cserélnek.

Ha kézzel szerkeszted az oldalt az adminban és **eltávolítod** a `<!-- whoopy-legal:vN -->` megjegyzést, a sync nem írja felül.
## Megjegyzés

Ez **nem** teljes Shopify parity (nincs themes editor, app store, POS) — a bolt backoffice magja van meg, amit a sidebar ígér.
