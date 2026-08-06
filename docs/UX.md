# Vásárlói élmény (Whoopy) — schema v11

| Funkció | Hol |
|---------|-----|
| Keresés + autocomplete | `/search`, `/api/suggest`, fejléc |
| Csomagpont (Foxpost/Packeta/GLS stub) | kosár → `/api/pickup-points` |
| Számlázási ≠ szállítási cím | checkout |
| Vendég rendelés link | e-mail `?t=access_token` |
| Elhagyott kosár e-mail | Admin → Elhagyott kosarak → küldés |
| Hírlevél kampány | Admin → Hírlevél → küldés |
| Összehasonlítás | `/compare` + termék gomb |
| Nemrég nézett | `/recent` (session) |
| Variánsok | `Offer.variant_label` + `Product.variant_axes` |
| Ajándékutalvány | kosár · demo: `WHOOPY5K`, `AJANDEK10K` |
| Hűségpont | account + kosár beváltás · demo vásárló: 500 pont |
| Chat | lebegő `?` → `/contact` + opcionális widget HTML a Beállításokban |

Éles csomagpont API / Tawk később env + kulcs alapján cserélhető.
