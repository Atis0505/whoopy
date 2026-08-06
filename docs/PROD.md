# Produkszállítás (hardening)

Rövid checklist Whoopy éles indításához.

## 1. Secret-ek

Másold a `.env.example` → `.env`, és cseréld:

| Változó | Megjegyzés |
|---------|------------|
| `ENVIRONMENT=production` | Bekapcsolja a prod védelmeket |
| `SECRET_KEY` | Hosszú random (session cookie) |
| `API_KEY` | Management API |
| `ADMIN_PASSWORD` | Ne legyen `admin1234` |
| `WEBHOOK_SECRET` | ERP webhook HMAC |

Indításkor a log figyelmeztet / errorozik, ha még `dev-change-me` értékek vannak.

## 2. Adatbázis

**Dev:** SQLite (alap).  
**Prod:** Postgres:

```env
DATABASE_URL=postgresql+psycopg2://whoopy:JELSZO@127.0.0.1:5432/whoopy
SEED_ON_STARTUP=false
```

Telepítés: `pip install psycopg2-binary` (benne a `requirements.txt`-ben).

- Production / Postgres: **soha nem törli** a DB-t schema bumpnál.
- Dev SQLite: schema version bump továbbra is újraseedelhet.

## 3. HTTPS / host

```env
FORCE_HTTPS=true
SESSION_HTTPS_ONLY=true
PUBLIC_BASE_URL=https://whoopy.hu
TRUSTED_HOSTS=whoopy.hu,www.whoopy.hu
```

Reverse proxy (Caddy / nginx / Cloudflare) terminálja a TLS-t; a app `FORCE_HTTPS` redirectel HTTP→HTTPS.

## 4. Rate limit

`/api/v1/*` alapból **120 req / perc / IP** (`RATE_LIMIT_API_PER_MINUTE`).  
Kikapcsolás: `RATE_LIMIT_ENABLED=false`.

## 5. Security headerek

Minden válasz: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, prod-ban `HSTS`.

## 6. Docs / seed

```env
DOCS_ENABLED=false
SEED_ON_STARTUP=false
```

Health check (LB): `GET /healthz` — auth nélkül.

## 7. Indítás

```bash
cd "C:\Users\korom\Személyes\taxonomy-marketplace"
.\.venv\Scripts\activate
pip install -r requirements.txt
# .env beállítva
uvicorn app.main:app --host 0.0.0.0 --port 8090 --workers 2
```

Ne használd `--reload`-ot productionben.

Docker: lásd [`DEPLOY.md`](DEPLOY.md) (`Dockerfile` + `docker-compose.yml`).

## CORS (ha kell)

```env
CORS_ORIGINS=https://whoopy.hu,https://www.whoopy.hu
```
