# EU webshop funkciók (Whoopy)

Schema **v9**. Rövid áttekintés.

| Funkció | URL / hol |
|---------|-----------|
| Cookie consent (GDPR) | footer banner → session |
| Jogi oldalak | `/pages/aszf`, `adatvedelem`, `sutik`, `impressum`, `szallitas`, `visszakuldes`, `rolunk` |
| Jogi tartalom sync | `app/content/legal_pages.py` · startup `ensure_default_cms_pages` (verziójel) |
| SEO | `/robots.txt`, `/sitemap.xml`, Product JSON-LD |
| ÁFA (bruttó árak) | kosár/rendelés nettó+ÁFA; ország szerinti rate stub |
| Számla (nyomtatható) | `/order/{n}/invoice` |
| Számlázz.hu | stub / dry-run / éles — `docs/SZAMLAZZ.md` |
| E-mail stub | SMTP vagy `data/email_outbox/` |
| Tracking | `/track` + admin szállítmány tracking |
| Kapcsolat | `/contact` |
| GYIK | `/faq` |
| Szűrők | főoldal: márka, ár, készlet, rendezés |
| Kívánságlista | `/wishlist` |
| Vélemények | termékoldal |
| Készlet-értesítő | fogyott termék |
| Visszaküldés (14 nap) | `/returns` |
| Checkout ÁSZF elfogadás | kötelező checkbox → ÁSZF + adatvédelem + elállás |
| A11y | skip-link, aria label-ek |

### Jogi tartalom (rövid)

Forrás: `app/content/legal_pages.py` · részletes doc: [`LEGAL.md`](LEGAL.md).

Cégadatok az admin Beállításokból (`{{company_name}}` stb.). Startup sync verziójellel (`<!-- whoopy-legal:vN -->`).

Rendszerleírás: [`AI_SYSTEM.md`](AI_SYSTEM.md)
