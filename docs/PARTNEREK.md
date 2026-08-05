# Partnerek és belső marketplace ops

A partnerek **források, ahonnan a Whoopy vásárol** — nem önálló eladók a bolton. Nincs supplier portal.

## Admin menü (Beszerzés / partnerek)

| Oldal | URL | Ki |
|-------|-----|----|
| Partnerek böngésző | `/admin/partners` | staff |
| Partner katalógus | `/admin/partners/{id}` | staff (szerkesztés: admin) |
| Beszerzési nézet | `/admin/procurement` | staff |
| Staging review | `/admin/staging` | admin |
| Feed források | `/admin/feeds` | admin |
| Árazási szabályok | `/admin/pricing-rules` | admin |
| GTIN dedup | `/admin/dedup` | admin |
| Partner KPI | `/admin/partner-kpi` | admin |

A klasszikus beszállító CRUD továbbra is: `/admin/suppliers`.

## Folyamat

1. **Feed** (`csv` / `json` / `url_json`) → `StagingListing` (`pending`)
2. **Staging** review → Publish → `Product` + `Offer` (GTIN egyezésnél meglévő termékhez)
3. **Árazás**: `cost_price` + `PricingRule` (`margin_percent` / `fixed_markup`) → listaár
4. **Buy-box**: `cheapest` | `fastest` | `preferred_supplier` + `Offer.preferred_source` / `Supplier.preferred`
5. **Rendelés** → **Beszerzés**: nyitott tételek partnerenként
6. **Dedup**: azonos GTIN termékek merge (ajánlatok a keep termékre)

## CSV oszlopok (alap)

`sku`, `gtin`, `title`, `description`, `brand`, `image_url`, `price`, `cost`, `stock`, `lead_days`

Field map JSON példa: `{"gtin":"ean","title":"name","cost":"net"}`

## Schema

Schema verzió **8** — új táblák: `feed_sources`, `feed_runs`, `staging_listings`, `pricing_rules`; bővítések: `suppliers.dropship_available`, `preferred`; `offers.cost_price`, `preferred_source`.

## Üzleti szabály

- Dropship csak ha a partner kínálja (`dropship_available`) — Whoopy dönt.
- Partner nem hirdet a storefronton; a vevő Whoopy ajánlatokat lát.
