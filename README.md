# HouseAccount AI Pricing Model

An AI pricing engine for the HouseAccount marketplace. Given a homeowner's booking —
a service category, a ZIP, and a free-text description of the job — it returns a price
range, a single point estimate, and a **calibrated confidence**, in well under two
seconds. It's built to beat HouseAccount's existing pricing baseline on the jobs that
matter most: real, messy, one-off requests.

The headline result, measured by leakage-free cross-validation:

| Metric | Baseline | This model | |
|---|---|---|---|
| Blended MAPE (411 priced jobs) | 11.6% | **10.85%** | ✅ beats |
| Real-only MAPE (~27 real jobs) | ~40% | **29.86%** | ✅ beats |

## How it works

The model doesn't price from scratch — it **corrects the previous model**. HouseAccount's
existing estimate (`original_estimate`) is already good on routine jobs, so a from-scratch
model would mostly relearn it and add noise. Instead, a gradient-boosted regressor predicts
the *residual* — `log(final_price) − log(original_estimate)` — from the signals the old model
ignored: the scope read out of the description, the ZIP's region, the subtype, urgency, and
seasonality. The correction is near zero where the prior is already right and meaningful where
it isn't (the hard, unique, real jobs).

Two things make the estimate trustworthy:

- **Confidence intervals** come from *normalized split-conformal prediction* — distribution-free,
  and scaled by how uncertain the previous model was, so a hard job reads as less certain than
  an easy one.
- **Out-of-distribution calibration**: a job whose midpoint is over $5,000, whose interval is
  wider than 3× the typical range, or whose category sits outside the 10 production verticals is
  passed through with **confidence forced below 0.5** — never rejected, just flagged so the
  marketplace can route it.

Scope extraction is the **hybrid** piece: an LLM (temperature 0, cached) reads structured
signals — complexity, labor hours, area, material tier — out of the free text where regex sees
nothing. The deterministic keyword extractor is a tested fallback, and the model beats both
baselines with *or* without the LLM, so accuracy never hard-depends on an API being reachable.

## Architecture

Three layers, cleanly separated:

```
  Browser / HouseAccount
          │  POST /pricing-estimate   (bearer)         ← the graded Appendix A contract
          │  POST /demo/estimates     (no bearer)       ← the playground the UI calls
          ▼
  ┌─────────────────────┐   JSON     ┌──────────────────────────────┐
  │  api/   Rails 8 API  │ ─────────▶ │ model_service/  Python/FastAPI│
  │  auth · validation · │   /predict │ features → model → conformal  │
  │  error shapes · UI · │ ◀───────── │ intervals → confidence → OOD  │
  │  outbound staging    │            │ (+ LLM scope extraction)      │
  └─────────────────────┘            └──────────────────────────────┘
```

- **`api/` (Rails)** owns the HTTP contract: bearer auth (`secure_compare`), required-field
  validation, the exact Appendix A error bodies, the `{ ok: true, … }` wrapper, the best-effort
  outbound post into the booking flow, and serving the single-page demo UI.
- **`model_service/` (Python)** owns the brain: data cleaning, feature engineering, the trained
  model, conformal intervals, confidence, and OOD calibration.

Keeping the LLM and the model in the Python service, and the contract in Rails, means each side
is testable in isolation — Rails request specs with a stubbed model, Python tests with no HTTP
and no API key.

## Run it locally (≈10 minutes)

**Prerequisites:** Ruby 3.4 + Bundler (via `rbenv`), Python 3.11 + [`uv`](https://docs.astral.sh/uv/),
and an OpenAI API key. The historical dataset is not in the repo (it's the client's data) — place
the CSV at `data/raw/houseaccount_pricing_sample.csv`.

```bash
# 1. Secrets — copy the template and fill in your key
cp .env.example .env
#    set OPENAI_API_KEY=...  and  GAUNTLET_PRICING_SECRET=$(openssl rand -hex 32)

# 2. Python model service
cd model_service && uv sync
uv run python scripts/train.py          # trains the model, writes model/ + docs/TEST_RESULTS.md
set -a; . ../.env; set +a
uv run uvicorn service.main:app --port 8010

# 3. Rails API (new terminal)
cd api && bundle install
set -a; . ../.env; set +a
MODEL_SERVICE_URL=http://127.0.0.1:8010 bin/rails server -p 3001
```

Open <http://127.0.0.1:3001> for the live demo. Or hit the contract directly:

```bash
curl -X POST http://127.0.0.1:3001/pricing-estimate \
  -H "Authorization: Bearer $GAUNTLET_PRICING_SECRET" \
  -H 'Content-Type: application/json' \
  -d '{"job_id":"demo","service_category":"Plumbing","zip_code":"78704",
       "job_description":"50-gallon gas water heater, pilot won'\''t stay lit"}'
```

## Verify everything

```bash
scripts/verify.sh          # both stacks: rubocop · rspec · ruff · mypy · pytest
make train                 # reproduce the MAPE numbers in docs/TEST_RESULTS.md
```

## More

- **Modeling approach & model card:** [docs/MODELING_APPROACH.md](docs/MODELING_APPROACH.md)
- **API contract:** [docs/API.md](docs/API.md) (mirrors Appendix A)
- **Deployment:** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Test results:** [docs/TEST_RESULTS.md](docs/TEST_RESULTS.md)
- **AI usage log:** [AI_USAGE.md](AI_USAGE.md)

## A note on secrets

The OpenAI key lives only in an untracked `.env` (local) or the platform secret store (prod) —
never committed, never sent to the browser. Rotate it after the evaluation is done.
