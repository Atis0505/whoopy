# Számlázz.hu integráció (Whoopy)

Schema **v10**. Hivatalos Agent API: https://docs.szamlazz.hu/

## Állapot

| Mód | Mikor | Mit csinál |
|-----|-------|------------|
| **Kikapcsolva** (alap) | `SZAMLAZZ_ENABLED=false` | HTML számla marad (`/order/{n}/invoice`) |
| **Dry-run** | `ENABLED=true`, üres `AGENT_KEY` | XML → `data/szamlazz_outbox/{order}.xml` |
| **Éles** | `ENABLED=true` + Agent kulcs | POST `https://www.szamlazz.hu/szamla/` → számlaszám + opcionális PDF |

## Env

```env
SZAMLAZZ_ENABLED=true
SZAMLAZZ_AGENT_KEY=...          # Számlázz fiók → Agent kulcs
SZAMLAZZ_ESZAMLA=true
SZAMLAZZ_DOWNLOAD_PDF=true
SZAMLAZZ_AUTO_ON_PAID=true      # fizetés után automatikus kiállítás
```

## Hol kapcsolódik

- Automatikus: `mark_order_paid` → `maybe_auto_invoice` (`app/services/szamlazz.py`)
- Kézi: Admin rendelés → **Számla kiállítása / dry-run**
- Mezők az `orders` táblán: `invoice_status`, `invoice_number`, `invoice_provider`, `invoice_pdf_path`, `invoice_error`

## Élesítés checklist

1. Számlázz.hu fiók + Agent kulcs
2. Eladó adatok a Számlázz felületen (adószám, bank)
3. `.env` kitöltése, `SZAMLAZZ_ENABLED=true`
4. Egy demo rendelés → fizetés → ellenőrizd a számlát a Számlázz UI-ban
5. Productionben ne hagyd dry-run-on (üres kulcs)

A HTML számla továbbra is elérhető belső / ügyfélszolgálati nézetként.
