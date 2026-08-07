# Jogi / tájékoztató oldalak (Whoopy)

Magyar és EU fogyasztói / GDPR sablonok a CMS-ben. **Nem ügyvédi vélemény** — éles indulás előtt töltsd ki a cégadatokat, és javasolt jogászi átnézés.

## Oldalak

| Slug | URL | Tartalom |
|------|-----|----------|
| `aszf` | `/pages/aszf` | Általános szerződési feltételek |
| `adatvedelem` | `/pages/adatvedelem` | Adatvédelmi tájékoztató (GDPR) |
| `sutik` | `/pages/sutik` | Süti / cookie tájékoztató |
| `impressum` | `/pages/impressum` | Impresszum, panasz / békéltető / ODR / NAIH |
| `szallitas` | `/pages/szallitas` | Szállítási tájékoztató |
| `visszakuldes` | `/pages/visszakuldes` | 14 napos elállás + minta nyilatkozat |
| `rolunk` | `/pages/rolunk` | Családi vállalkozás bemutatkozás |

Kapcsolódó UI: footer „Jogi”, cookie banner → sütik/adatvédelem, `/faq`, `/contact`, `/returns`, checkout ÁSZF checkbox.

## Forráskód

| Fájl | Szerep |
|------|--------|
| `app/content/legal_pages.py` | HTML sablonok + `LEGAL_CONTENT_VERSION` |
| `app/services/store_settings.py` | `ensure_default_cms_pages`, `render_cms_placeholders` |
| `app/main.py` startup | sync seed nélkül is |
| `app/routers/store.py` | `/pages/{slug}` + checkout `accept_terms` |

## Cégadatok (placeholderek)

Admin → **Beállítások**: cégnév, cím, adószám, EU ÁFA, support e-mail/telefon, ügyfélfogadás.

A CMS body-ban: `{{company_name}}`, `{{company_address}}`, `{{company_tax_id}}`, `{{company_eu_vat}}`, `{{support_email}}`, `{{support_phone}}`, `{{business_hours}}`, `{{store_name}}`, `{{domain}}` — megjelenítéskor cserélődnek.

## Verzió sync

Minden seedelt jogi oldal elején: `<!-- whoopy-legal:vN -->`.

- Startup / seed: ha hiányzik a marker, régi `vN`, vagy régi „minta” placeholder → felülírás.
- Ha az admin **eltávolítja** a markert (és a szöveg hosszú, nem minta) → a sync **nem** írja felül.
- Új sablon szöveghez: növeld `LEGAL_CONTENT_VERSION`-t.

## Checklist éles előtt

1. Beállítások: cégnév, székhely, adószám, EU ÁFA, e-mail, telefon  
2. Átnézni ÁSZF / adatvédelem / elállás szöveget  
3. Checkout ÁSZF checkbox működik  
4. Cookie banner + `/pages/sutik`  
5. Impresszumban békéltető / hatóság linkek OK  

Lásd még: [`EU_SHOP.md`](EU_SHOP.md) · [`ADMIN.md`](ADMIN.md)
