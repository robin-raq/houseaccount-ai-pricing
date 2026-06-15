# API Reference

Implements the Appendix A contract. The Rails service is the public surface; it calls the
internal Python model service for the estimate.

## `POST /pricing-estimate` — the contract (bearer-protected)

The endpoint HouseAccount calls during evaluation.

**Auth:** `Authorization: Bearer <GAUNTLET_PRICING_SECRET>`, constant-time compared
(`ActiveSupport::SecurityUtils.secure_compare`). Content type `application/json`.

### Request

| Field | Required | Notes |
|---|---|---|
| `job_id` | yes | Stable id, echoed back |
| `service_category` | yes | Any string; the 18 trained categories are recognized |
| `zip_code` | yes | 5-digit US ZIP |
| `job_description` | yes | Free text — the scope-extraction surface |
| `service_subtype` | no | Hint, not validated |
| `deadline` | no | One of the four canonical strings |
| `booking_month` | no | `YYYY-MM` |
| `original_estimate`, `original_estimate_lo`, `original_estimate_hi` | no | Previous-model prior; used as the correction base when present |

### Response — `200`

```json
{
  "ok": true,
  "job_id": "abc123",
  "estimate_lo": 1565.0,
  "estimate_hi": 2030.0,
  "estimate_midpoint": 1823.0,
  "confidence": 0.86,
  "model_version": "houseaccount-pricing-v1.0.0"
}
```

`estimate_lo ≤ estimate_midpoint ≤ estimate_hi`; `confidence ∈ [0, 1]`.

### Errors

| Code | Body | When |
|---|---|---|
| `401` | `{"error":"Unauthorized"}` | missing/invalid bearer |
| `400` | `{"error":"<field> required"}` | a required field is blank |
| `400` | `{"error":"Malformed JSON"}` | body isn't valid JSON |
| `405` | `{"error":"Method not allowed"}` | non-POST to the path |

The auth fails **closed**: a blank/unset `GAUNTLET_PRICING_SECRET` rejects every request (it never
accepts an empty token), and in production the app **refuses to boot** if the secret is unset
(`config/initializers/pricing_secret.rb`). The compare hashes both sides, so it's constant-time
regardless of token length.

## `POST /demo/estimates` — the public playground (no bearer)

What the demo UI calls. Same booking input and validation, but no auth (the secret stays
server-side) and a **richer** response: it adds `scope` (the extracted signals), `ood_reasons`,
`latency_ms`, and `staging_status`. Each call is recorded in an in-memory log.

## `GET /demo/estimates` — recent-request log

`{ "estimates": [ { job_id, service_category, estimate_midpoint, confidence, latency_ms, staging_status }, … ] }`

## `GET /demo/model` — model metadata

Proxies the model service's `/meta`: version, the MAPE numbers vs baseline (shipped and
deterministic), per-category breakdown, and the production / trained category lists. Powers the
Evaluation and Model Card screens.

## Outbound: the booking-flow integration

After producing an estimate, the demo path makes a **best-effort** POST to the HouseAccount
booking-create staging endpoint (`STAGING_BOOKINGS_URL` + `STAGING_APP_NAME` + `STAGING_SIGNING_SECRET` (HMAC-signed)). It never
blocks or fails the response: with no URL configured it reports `skipped`; on error it reports the
error and moves on. This is the "booking input in → price out → posted to staging" loop; drop in
real staging credentials to activate it.

## Internal: `POST /predict` (Python model service)

Not public. Rails posts the booking payload; the service returns
`{ estimate_lo, estimate_hi, estimate_midpoint, confidence, model_version, scope, ood_reasons,
latency_ms }`. `GET /health` and `GET /meta` round it out.
