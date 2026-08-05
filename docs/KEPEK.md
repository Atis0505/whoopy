# Termékképek feltöltése

Helyi tároló + Management API + admin UI.

## Hol tárolódik?

```
data/uploads/products/{product_id}/{uuid}.jpg
```

Nyilvános URL: `/media/products/{product_id}/{fájlnév}`  
(pl. `http://127.0.0.1:8090/media/products/3/abc….webp`)

A feltöltött fájlok **nincsenek** a Gitben (`.gitignore`: `data/uploads/`).

Engedélyezett: **jpg / png / webp / gif**, max **5 MB**.

Az elsődleges kép beíródik a `Product.image_url` mezőbe (Merchant feed / listák).

## Admin UI

1. Belépés: `admin@whoopy.local` / `admin1234`
2. **Admin → Termékek**
3. A sorban: fájlválasztó → Feltöltés (opcionálisan „elsődleges”)
4. ★ = elsődleges, × = törlés

## API (X-API-Key)

| Metódus | Útvonal | Leírás |
|---------|---------|--------|
| GET | `/api/v1/products/{id}/images` | Lista |
| POST | `/api/v1/products/{id}/images` | Multipart feltöltés |
| POST | `/api/v1/products/{id}/images/{image_id}/primary` | Elsődleges |
| DELETE | `/api/v1/products/{id}/images/{image_id}` | Törlés |

### curl példa

```bash
curl -s -X POST "http://127.0.0.1:8090/api/v1/products/1/images" \
  -H "X-API-Key: whoopy-dev-api-key-change-me" \
  -F "file=@C:/temp/kulacs.jpg" \
  -F "alt=Whoopy kulacs" \
  -F "set_primary=true"
```

A termék JSON (`ProductOut`) tartalmazza az `images[]` tömböt is.

## Schema

`ProductImage` tábla — schema verzió **v6**.
