# Kategória böngészés (alkategória-kártyák)

Google Product Taxonomy fa minden mélységben.

## Viselkedés

| Állapot | UI |
|---------|-----|
| Kevés termék az ágban (≤ **12**) | Terméklista (mint eddig) + alkategória chip-ek ha van gyermek |
| Sok termék (> **12**) **és** van nem üres alkategória | **Alkategória-kártyák** (kép + név + darabszám) |
| `?view=products` | Mindig a terméklista (lapozva) |

Küszöb: `SUBCATEGORY_THRESHOLD` a `app/services/category_browse.py`-ban.

Kártyakép: először mintatermék az alkategória ágából, különben stock fotó kulcsszó alapján (Electronics / Headphones / …).

Breadcrumb: Taxonomy → szülők → aktuális.

Hivatalos teljes fa: `python -c "from app.services.taxonomy import ensure_taxonomy_file, load_taxonomy_file; ..."` vagy `docs/MERCHANT.md` taxonomy import.
