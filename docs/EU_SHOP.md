# EU webshop funkciók (Whoopy)

Schema **v9**. Rövid áttekintés.

| Funkció | URL / hol |
|---------|-----------|
| Cookie consent (GDPR) | footer banner → session |
| Jogi oldalak | `/pages/aszf`, `adatvedelem`, `impressum`, `szallitas`, `visszakuldes` |
| SEO | `/robots.txt`, `/sitemap.xml`, Product JSON-LD |
| ÁFA (bruttó árak) | kosár/rendelés nettó+ÁFA; ország szerinti rate stub |
| Számla (nyomtatható) | `/order/{n}/invoice` |
| E-mail stub | SMTP vagy `data/email_outbox/` |
| Tracking | `/track` + admin szállítmány tracking |
| Kapcsolat | `/contact` |
| GYIK | `/faq` |
| Szűrők | főoldal: márka, ár, készlet, rendezés |
| Kívánságlista | `/wishlist` |
| Vélemények | termékoldal |
| Készlet-értesítő | fogyott termék |
| Visszaküldés (14 nap) | `/returns` |
| A11y | skip-link, aria label-ek |

Rendszerleírás: [`AI_SYSTEM.md`](AI_SYSTEM.md)
