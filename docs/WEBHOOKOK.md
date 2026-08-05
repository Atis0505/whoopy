# Webhook-ek (Whoopy → ERP)

Whoopy eseményeket küld HTTP POST-tal a beállított URL-re (tipikusan az ERP).

## Események

| Event | Mikor |
|-------|--------|
| `order.created` | Új rendelés a checkout után |
| `order.paid` | Online fizetés sikeres |
| `order.payment_failed` | Fizetés sikertelen / megszakítva |
| `order.status_changed` | Admin / API státuszváltás |
| `shipment.updated` | Tracking / szállítmány státusz |

## Bekapcsolás (Whoopy)

```env
WEBHOOK_ENABLED=true
WEBHOOK_URL=http://127.0.0.1:8010/api/v1/webhooks/whoopy
WEBHOOK_SECRET=whoopy-webhook-secret-change-me
```

Extra célok: Admin → **Webhook-ek**, vagy `POST /api/v1/webhooks`.

## Payload

```json
{
  "event": "order.paid",
  "sent_at": "2026-08-05T21:00:00Z",
  "source": "whoopy",
  "data": {
    "id": 12,
    "order_number": "TM-…",
    "status": "paid",
    "payment_status": "paid",
    "grand_total": 12990,
    "lines": [ … ],
    "shipments": [ … ]
  }
}
```

Headerek:

- `X-Whoopy-Event`: esemény név
- `X-Whoopy-Signature`: HMAC-SHA256 hex (`secret` + raw body)
- `Content-Type: application/json`

## ERP fogadó

`POST /api/v1/webhooks/whoopy`  
Secret: `WHOOPY_WEBHOOK_SECRET` (ugyanaz, mint a Whoopy `WEBHOOK_SECRET`).

Most: aláírás ellenőrzés + log. Később: `whoopy_orders` perzisztencia.

## API / admin

| Hol | Mit |
|-----|-----|
| Admin `/admin/webhooks` | Endpointok, teszt ping, delivery log |
| `GET /api/v1/webhooks/deliveries` | Küldési napló |
| `POST /api/v1/webhooks/test` | Teszt esemény |

Delivery-k a `webhook_deliveries` táblában (schema **v7**).
