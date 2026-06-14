# Deployment Guide

Two services, deployed independently: the **Rails API** (public) and the **Python model
service** (called by Rails). Railway is the reference platform; any host that can run a Ruby
web service and a Python web service works.

## Local

See the README's "Run it locally" section. In short: `make model-service` in one terminal,
`make api` in another, both reading secrets from `.env`. Visit <http://127.0.0.1:3001>.

## Railway (reference)

Both services live in this one repo, so create **two Railway services** in one project, each
pointed at a different root directory. Each subdirectory has a `railway.toml` with its start
command and health check.

### 1. Model service (Python)

- New service → deploy from this repo → **Root Directory: `model_service`**.
- Variables: `OPENAI_API_KEY=<your key>`.
- Railway (Nixpacks) detects `pyproject.toml` + `uv.lock`, runs `uv sync`, and starts
  `uv run uvicorn service.main:app --host 0.0.0.0 --port $PORT`. The trained model ships in the
  repo (`model_service/model/model.joblib`), so there's no training at deploy time.
- Health check: `/health`. Note this service's URL.

### 2. Rails API (public)

- New service → same repo → **Root Directory: `api`**.
- Variables:
  - `GAUNTLET_PRICING_SECRET` — the bearer secret HouseAccount will use (`openssl rand -hex 32`).
  - `MODEL_SERVICE_URL` — the model service's URL from step 1. Prefer Railway's **private
    networking** (`http://<model-service>.railway.internal:<port>`) so the model service isn't
    public; the public URL also works for a quick demo.
  - `SECRET_KEY_BASE` — `openssl rand -hex 64`.
  - `RAILS_ENV=production`.
  - Optional: `STAGING_BOOKINGS_URL`, `STAGING_BOOKINGS_TOKEN` to activate the outbound post.
- Starts `bundle exec rails server -b 0.0.0.0 -p $PORT`; serves the demo UI and the contract.
- Health check: `/up`. This service's public URL is the demo.

### 3. Verify the deployment

```bash
# the contract (bearer required)
curl -X POST https://<api>.up.railway.app/pricing-estimate \
  -H "Authorization: Bearer $GAUNTLET_PRICING_SECRET" \
  -H 'Content-Type: application/json' \
  -d '{"job_id":"deploy-check","service_category":"Plumbing","zip_code":"78704",
       "job_description":"50-gallon gas water heater, replace"}'

# the live UI + flows (headless)
node scripts/verify_live.mjs https://<api>.up.railway.app
```

## Giving HouseAccount the evaluation endpoint

The graded endpoint is `POST https://<api>.up.railway.app/pricing-estimate`. Share that URL and
the `GAUNTLET_PRICING_SECRET`. The endpoint accepts the Appendix A payload and returns the
estimate; it has no per-request rate limit by default.

## Notes & hardening

- **Secrets** are set in each platform's variable store, never in the repo. Rotate the OpenAI key
  after the evaluation.
- The model service has **no auth** — fine behind private networking; if exposed publicly, add a
  shared secret before any real traffic.
- The recent-request log is **in-memory**, so it resets on redeploy (it's a demo affordance, not a
  system of record).
- First request after a cold deploy pays a one-time LLM warmup; the service warms itself at boot,
  so subsequent requests meet the <2s target.
