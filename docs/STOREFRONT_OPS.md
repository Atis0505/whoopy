# Storefront ops (Whoopy) — schema v14 + státusz v17

| Funkció | Hol |
|---------|-----|
| Felső hirdetőszalag | Beállítások → ki/be, szöveg, link, szín, ütemezés · minden oldalon |
| Social ticker | Futó sáv: friss vásárlások + havi kedvencek + `topbar` kampányok |
| **Bolt státusz (3 fokozat)** | Dashboard / Beállítások · `storefront_status` |
| **Vevői előnézet** | Dashboard → „Vevői előnézet ↗” (új tab) · session flag · sárga sáv + kilépés |
| Feed hide | `closed` VAGY feed flag OFF → üres Google/Meta/Árukereső |
| Kampány toggle | `/admin/campaigns` → Bekapcsolva / Kikapcsolva |
| Free-ship progress | Kosár · küszöb a Beállításokban |
| Pending badge | Admin sidebar Rendelések |
| Készlet pill | Terméklista: ok / low / out |
| DEMO badge | `environment != production` |
| Ügyfélszolgálati órák | Beállítások → topbar + footer + contact |

## Bolt státusz fokozatok

| Státusz | Vásárló | Kosár / checkout | Admin | Dolgozó |
|---------|---------|------------------|-------|---------|
| `open` | teljes bolt | igen | igen | igen |
| `catalog_only` | böngészés + banner | **nem** (gombok elrejtve, POST tiltva) | igen | igen |
| `closed` | **egyoldalas** „bolt inaktív” (503) | — | **igen** (újra lehet nyitni) | **nem** (login tiltva) |

Üzenetek: `maintenance_message` (zárás), `orders_paused_message` (rendelés szünet).  
Legacy: `maintenance_mode=true` ≡ `closed`.

### Vevői előnézet (admin)

- Dashboard: **Vevői előnézet ↗** → `/admin/preview` (új böngészőtab).
- Session: `storefront_preview=1` + admin user → a zárt/szünetelt bolt mellett is teljes vevői UI (kosár is).
- A nyilvános látogatók továbbra is a valódi státuszt kapják (záró oldal / rendelés szünet).
- Kilépés: sárga sáv → `/admin/preview/exit`.

**Reszponzív:** mobil / tablet breakpointok a `style.css` + `admin.css` fájlokban.
