# Deploy / éles domain

Részletes hardening: [`PROD.md`](PROD.md). Ez a rövid „menjünk élőbe” útmutató.

## A) Natív (Windows / Linux VM)

1. Másold `.env.example` → `.env`, állítsd:
   - `ENVIRONMENT=production`
   - erős `SECRET_KEY`, `API_KEY`, `ADMIN_PASSWORD`, `WEBHOOK_SECRET`
   - `DATABASE_URL=postgresql+psycopg2://...`
   - `PUBLIC_BASE_URL=https://whoopy.hu`
   - `MEDIA_PUBLIC_BASE=https://cdn.whoopy.hu` (vagy ugyanaz mint PUBLIC)
   - `FORCE_HTTPS=true`, `SESSION_HTTPS_ONLY=true`
   - `TRUSTED_HOSTS=whoopy.hu,www.whoopy.hu`
   - `SEED_ON_STARTUP=false`, `DOCS_ENABLED=false`
   - `SIMPLEPAY_SANDBOX=false`, `SIMPLEPAY_ALLOW_DEMO_FALLBACK=false` (éles SimplePay)
2. Reverse proxy (Caddy / nginx / Cloudflare) → `127.0.0.1:8090`
3. Indítás:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8090 --workers 2
```

4. Health: `GET https://whoopy.hu/healthz`
5. ERP `.env`: `WHOOPY_API_URL=https://whoopy.hu/api/v1`, ugyanaz a kulcs; `WHOOPY_AUTOSYNC_ENABLED=true` ha kell.

## B) Docker Compose

```bash
cp .env.example .env   # töltsd ki
docker compose up --build -d
```

- App: `:8090`
- Postgres: host `:5433` → container `5432`
- Volume: `whoopy_uploads` a képeknek

## C) CDN képek

1. Cloudflare / nginx cache a `/media/products/*` path-ra **vagy**
2. Állíts `MEDIA_PUBLIC_BASE`-t a CDN originre, ami a feltöltött fájlokat szolgálja ki.
3. A primary `Product.image_url` abszolút URL lesz (`absolute_media_url`).

Külső `image_url` (ERP push) továbbra is működik CDN nélkül.

## D) SimplePay sandbox checklist

1. OTP sandbox merchant + secret
2. `PAYMENT_PROVIDER=simplepay`, `SIMPLEPAY_SANDBOX=true`
3. Publikus `PUBLIC_BASE_URL` (ngrok / tunnel ha lokális)
4. IPN URL: `{PUBLIC_BASE_URL}/pay/webhook/simplepay`
5. Signature ellenőrzés be van kapcsolva; sandboxban hiányzó Signature csak ha `SIMPLEPAY_ALLOW_DEMO_FALLBACK=true`
