# Marketing (Whoopy) — schema v12

| Funkció | URL / hol |
|---------|-----------|
| Google Merchant | `/feeds/google-merchant.xml` |
| Meta / FB / IG Shop | `/feeds/meta-catalog.xml` |
| Árukereső | `/feeds/arukereso.xml` |
| UTM capture | bármely oldal `?utm_source=&utm_medium=&utm_campaign=` → session → kosár → rendelés |
| Affiliate link | `/go/aff/PARTNER10?next=/` (demo: `PARTNER10`, `BLOGGER`) |
| Kampány klikk | `/go/c/{id}` (impresszió a főoldalon, klikk számláló) |
| Hero A/B | kampány `ab_group` A/B + session bucket |
| Admin | `/admin/marketing` — feedek, UTM riport, affiliate, A/B stats |

**Nincs** teljes theme editor / Shopify A/B app — csak hero A/B + attribúció.
