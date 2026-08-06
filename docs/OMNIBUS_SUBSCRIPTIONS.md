# Omnibus ártörténet + ismétlődő rendelések — schema v15

## Omnibus / PriceHistory

| Funkció | Hol |
|---------|-----|
| Árváltozás napló (`previous_price`, `source`) | `services/compliance.py` → `set_offer_price` / `record_offer_price` |
| API / bulk / staging / admin inventory | mind `set_offer_price(... source=...)` |
| 30 nap legalacsonyabb | `lowest_price_30d` · termékoldal Omnibus szöveg |
| Guard (admin figyelmeztetés) | `omnibus_discount_ok` · `/admin/inventory?omnibus=1` |
| Riporter | `/admin/price-history` |
| Snapshot seed | `snapshot_active_prices` |

Források: `api`, `api_bulk`, `staging`, `admin_inventory`, `seed`, `snapshot`.

## Automatikus újrarendelés (Subscription)

| Funkció | Hol |
|---------|-----|
| Model | `Subscription` + `SubscriptionLine` |
| Vásárló UI | `/account` · kosár „Ismétlés” · rendelésből |
| Router | `routers/subscriptions.py` |
| Fulfill + due runner | `services/subscriptions.py` |
| Admin | `/admin/subscriptions` · Run due / Run now |
| Startup | seed után `process_due_subscriptions` |
| GDPR | anonimizáláskor pause + inactive |

**Fizetés:** ismétlés COD/invoice/prepaid stub — új rendelés `pending` státusszal (mint a kézi checkout COD). Nincs tárolt kártya.

Intervallumok: 7 / 14 / 30 / 60 / 90 nap. Hiba esetén `last_error` + +1 nap retry.
