# Storefront ops (Whoopy) — schema v14

| Funkció | Hol |
|---------|-----|
| Felső hirdetőszalag | Beállítások → ki/be, szöveg, link, szín, ütemezés · minden oldalon |
| Social ticker | Futó sáv: friss vásárlások + havi kedvencek + `topbar` kampányok |
| Bolt zárás 1 gombbal | Dashboard → „Bolt zárása” · maintenance 503 a vásárlóknak · admin/login nyitva |
| Feed hide | Maintenance VAGY feed flag OFF → üres Google/Meta/Árukereső |
| Kampány toggle | `/admin/campaigns` → Bekapcsolva / Kikapcsolva |
| Free-ship progress | Kosár · küszöb a Beállításokban |
| Pending badge | Admin sidebar Rendelések |
| Készlet pill | Terméklista: ok / low / out |
| DEMO badge | `environment != production` |
| Ügyfélszolgálati órák | Beállítások → topbar + footer + contact |

**Reszponzív:** mobil / tablet breakpointok a `style.css` + `admin.css` fájlokban (sticky header, wrap header, sticky admin nav).
