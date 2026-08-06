# Logisztika + Compliance (Whoopy) — schema v13

## Logisztika

| Funkció | Hol |
|---------|-----|
| Futár címke stub (GLS / Foxpost / Packeta) | `services/carriers.py` → `data/carrier_outbox/` · Admin rendelés → Címke |
| Tracking sync stub | Admin → Tracking sync (pending→labeled→shipped→delivered) |
| Partial fulfill | Több szállítmány külön státusz; mind shipped/delivered → order `fulfilled`, részben → `partial` |
| Multi-warehouse | `Warehouse` modell · `/admin/warehouses` · checkout default WH a shipmentre |
| RMA címke + refund | `services/rma.py` → `data/rma_outbox/` · `/admin/returns` |

**Nincs** éles GLS/Foxpost API — outbox JSON stub, mint a Számlázz dry-run.

## Compliance

| Funkció | Hol |
|---------|-----|
| Cookie CMP (analytics/marketing) | Banner + `CookieConsentLog` · Consent Mode stub scripteket enged |
| GDPR export | `/account/export` JSON |
| GDPR törlés / anonimizálás | `/account/delete` (confirm: `TORLES`) |
| B2B ÁFA / reverse charge | Kosár `/cart/b2b` · `effective_vat_rate` · EU adószám formátum stub |
| Omnibus 30 nap legalacsonyabb ár | `PriceHistory` · termékoldal · seed snapshot |

## Seed

- Raktárak: `BUD-01` (default), `DEB-02`
- Aktív ajánlatok ársnapshotja Omnibushoz
