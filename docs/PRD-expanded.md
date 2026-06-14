# HouseAccount AI Pricing Model — Expanded PRD

> Source of truth: `prd.md` (Gauntlet brief + Appendix A API schema). This document keeps
> the original intent intact and adds the engineering detail the build needs so there is no
> ambiguity about *what* to build. Where the brief is silent, decisions are made explicitly
> and flagged. Appendix A is the binding external API contract.

---

## Original brief (intent, lightly cleaned)

Build an AI pricing model that, given a booking (job type, scope, location, free-text
description, attributes), returns an estimated price **plus a confidence score or range**.
It must combine internal pricing data with public knowledge to produce transparent,
booking-time estimates with confidence intervals that hold up across job types and regions.
The product is the **model**, not a lookup table.

The bar: homeowners trust the price enough to book without shopping the market; providers
trust it enough to accept without renegotiation. Impact metrics: estimate accuracy (MAPE),
booking conversion, provider acceptance, fulfillment without price adjustment.

**Must beat baseline on two MAPE numbers** computed from submitted predictions:
- **Blended MAPE** on the 411-row priced subset — baseline **11.6%** (median APE 8.3%).
- **Real-only MAPE** on the held-out real-job subset (~27 rows) — baseline **~40%**.

Top finalists may be re-scored on a held-out post-snapshot real dataset.

---

## Problem & users

- **Homeowner** (books a job): enters a service request in free text; needs a price they can
  trust *now*, with an honest sense of how sure the system is.
- **Provider** (fulfills the job): needs the estimate to match what the job actually costs so
  they accept without renegotiating.
- **HouseAccount marketplace** (routes the booking): needs a calibrated `confidence` it can
  route on — high confidence auto-books, low confidence routes to a human or a provider quote.

**The single most important flow:** booking input → price estimate `{lo, hi, midpoint}` +
calibrated `confidence` → rendered transparently (and posted to the booking flow). Everything
else in the product exists to prove that this flow is accurate, calibrated, and honest.

---

## Scope

### In scope
- A **Python model service** that turns a booking into `{estimate_lo, estimate_hi,
  estimate_midpoint, confidence}` using a trained gradient-boosted regressor + conformal
  prediction intervals, with LLM-assisted scope extraction from `job_description`.
- A **Rails API layer** implementing the Appendix A contract exactly: bearer auth, request
  validation, response/error shapes, the `{ ok: true, ... }` wrapper, and the outbound POST
  to the staging booking endpoint.
- **Confidence calibration** with explicit out-of-distribution (OOD) rules (below).
- A **thin demo UI** (4 screens) so a reviewer/video can see the flow, the calibration, the
  modeling approach, and the integration — without reading code.
- An **evaluation harness** (CLI + Make target) that reproduces both MAPE numbers from the
  dataset and writes them to `docs/TEST_RESULTS.md`.
- **Tests** for core pricing logic (Python) and integration boundaries (Rails request specs).

### Explicitly out of scope (prevents phantom features)
- No homeowner/provider accounts, auth UI, login, or user management.
- No real booking/scheduling/payments — the staging POST is the only booking-flow touchpoint.
- No provider marketplace, matching, messaging, or reviews.
- No multi-tenant isolation (single shared bearer secret, per Appendix A "Out of scope").
- No caching-control headers, webhooks, or async callbacks (Appendix A "Out of scope").
- No load testing (per brief; the 2s target is per-request only).
- **No hardcoded pricing tables.** Census/demographic joins are demographic *features*, not price lookups.

---

## Screens / routes (demo inventory — the contract Phase 3 mockup and Phase 4 build both satisfy)

The product is API-first; the UI is a transparency layer over it. Four screens, top-nav tabs,
all wired.

| Route | Screen | Purpose | Key components | Data shown |
|---|---|---|---|---|
| `/` (Estimate) | **Estimate Sandbox** (hero) | Enter a booking, get a priced estimate with calibrated confidence and a transparent breakdown | Booking form (category, subtype, zip, description, deadline, month, optional baseline estimate); "Get estimate" button; result card | `estimate_lo / midpoint / hi` as a range bar; `confidence` gauge with the 0.5 / 0.75 / 0.8 threshold bands; `model_version`; **"What the model saw"** panel (LLM-extracted scope signals); OOD flags + why; latency |
| `/evaluate` | **Evaluation** | Prove the model beats baseline | Metric cards (blended MAPE vs 11.6%, real-only MAPE vs 40%); pass/fail badges; per-category MAPE table; APE distribution chart | Our blended MAPE, median APE, real-only MAPE; baseline deltas; n per subset; per-category breakdown; date the eval was run |
| `/model` | **Model Card / How it works** | The documented modeling approach, in-product | Sections: data used, features, model type, **how confidence is calculated**, OOD rules, assumptions, known limitations | Feature list, training row counts, conformal coverage target, OOD thresholds, category-coverage tradeoff (10 production vs 18 trained) |
| `/api` | **API & Integration** | Show the live contract and the staging integration | Endpoint + auth doc; copy-paste `curl`; live "Try it" that calls the real endpoint; staging-POST status panel; recent request log | Request/response schema; last N requests (`job_id`, category, midpoint, confidence, latency, staging-post result) |

The mockup builds exactly these four; nothing else. Any nav item not in this table is a phantom and must not appear.

---

## Data model

Model-serving app, so "entities" are mostly value objects + a thin request log. Minimal persistence.

- **BookingInput** (request value object) — `job_id`, `service_category`, `service_subtype?`,
  `zip_code`, `job_description`, `deadline?`, `booking_month?`, `job_status?`,
  `original_estimate?`, `original_estimate_lo?`, `original_estimate_hi?`. (Appendix A request.)
- **ScopeSignals** (derived) — structured fields extracted from `job_description`:
  `size_value? + size_unit?` (e.g. 2-story / 20 windows / 50-gal), `quantity?`, `fixture_count?`,
  `material_tier? (economy|standard|premium)`, `complexity (low|medium|high)`,
  `est_labor_hours?`, `access_difficulty?`, `customer_supplies_parts?`. Source: LLM (temp 0,
  cached) with a regex/keyword fallback.
- **PriceEstimate** (response value object) — `estimate_lo`, `estimate_hi`, `estimate_midpoint`,
  `confidence` (clamped [0,1]), `model_version`, plus internal `ood_reasons[]` and `latency_ms`.
- **EvaluationResult** (computed offline, served as JSON) — per-subset: `n`, `mape`,
  `median_ape`, `baseline_mape`, `beats_baseline`; plus `per_category[]`. Persisted as a JSON
  artifact, surfaced by `/evaluate`.
- **RequestLog** (optional, in-memory ring or SQLite) — `job_id`, `received_at`, `category`,
  `midpoint`, `confidence`, `latency_ms`, `staging_post_status`. Powers `/api` recent-requests.
- **ModelArtifact metadata** — `model_version`, trained-at, training row counts, feature list,
  conformal target coverage, OOD thresholds. Bundled with the serialized model; surfaced by `/model`.

---

## AI surface (runtime — what the deployed OpenAI key powers)

1. **LLM scope extraction** (the one model call in the pricing path).
   - **Input:** `job_description` (+ `service_category`, `service_subtype` as context).
   - **System-prompt intent:** "You convert a homeowner's free-text home-service request into
     structured scope signals used to price the job. Return JSON only." Extract the
     ScopeSignals fields above; never invent a price.
   - **Output shape:** strict JSON matching ScopeSignals; `temperature = 0`; short max tokens;
     keyed cache by `sha256(category|subtype|description)` so repeated/eval inputs are deterministic.
   - **Where it renders:** the Estimate screen's "What the model saw" panel, and as model features.
   - **Fallback:** if the key is absent, the call errors, or it times out (budget ~700ms), a
     deterministic regex/keyword extractor fills the same fields. **The ML core alone beats
     baseline**, so the LLM is additive enrichment, never a hard dependency. This protects
     eval reproducibility and the <2s SLA.

2. **Demo narration (not a product surface):** OpenAI TTS in Phase 5 only, same key.

> The ML model, conformal intervals, and confidence math are fully deterministic. The only
> nondeterminism risk (the LLM) is pinned to temp 0 + cached + fallback.

### Confidence calculation (must be documented in `/model`)
- Base confidence derived from the **conformal prediction interval width** relative to the
  point estimate: a tight interval → high confidence, a wide interval → low confidence
  (monotonic mapping, clamped to [0,1]).
- **OOD overrides force `confidence < 0.5`** when any holds (do **not** reject or cap the input):
  - `estimate_midpoint > $5,000` (≈95th pct of training), OR
  - prediction interval `(hi − lo)` wider than **3× the median** observed training range, OR
  - `service_category` outside the **10 current production verticals**
    (electrical, exterior-cleaning, handyman, hvac, indoor-cleaning, irrigation,
    landscaping-lawn, pest-control, plumbing, tick-mosquito-treatment).
- Threshold convention surfaced in UI (from the codebase): `≥0.8` obvious, `0.5–0.8` ambiguous,
  `<0.5` guess; auto-action elsewhere uses `≥0.75`.

---

## External integrations

- **OpenAI API** — scope-extraction (runtime) + TTS (demo). Key via env/secret store only.
- **Outbound staging POST** — `POST` the produced estimate to HouseAccount's booking-create
  staging endpoint (the brief's "end-to-end: ... posted to the staging endpoint"). URL + token
  are configurable env vars; if absent, the call is **stubbed and logged** (status `skipped`),
  and `/api` shows that honestly. This is the *outbound* direction; it is distinct from the
  inbound Appendix A contract.
- **Census/demographic join (optional feature enrichment)** — a static ZIP→median-household-income
  (and/or region) table joined at feature time. A demographic signal, **not** a price table.
  If unavailable, the model falls back to ZIP-prefix (zip3) regional features.

---

## Acceptance criteria (reviewer + live-verify checklist)

**API contract (Appendix A):**
- [ ] Valid booking → `200` with `ok:true`, echoed `job_id`, `estimate_lo ≤ estimate_midpoint ≤ estimate_hi`, `confidence ∈ [0,1]`, non-empty `model_version`, end-to-end **< 2s**.
- [ ] Missing bearer / wrong secret → `401 {"error":"Unauthorized"}` (constant-time compare).
- [ ] Missing `job_id`/`service_category`/`zip_code`/`job_description` → `400 {"error":"<field> required"}`.
- [ ] Malformed JSON → `400 {"error":"Malformed JSON"}`. Non-POST → `405 {"error":"Method not allowed"}` (JSON).
- [ ] Boot-time throw if the bearer secret env var is unset.

**Calibration:**
- [ ] Midpoint > $5k, OR interval > 3× median, OR non-production category → `confidence < 0.5`, input **passed through** (not rejected/capped).

**Accuracy (the bar):**
- [ ] Blended MAPE on the 411-row priced subset **< 11.6%** (and report median APE).
- [ ] Real-only MAPE on the held-out real-job subset **< 40%**.
- [ ] Both reproducible via one command (`make eval` / CLI), output captured to `docs/TEST_RESULTS.md`.

**Product + integration:**
- [ ] All 4 screens reachable and functional on the live URL; Estimate flow calls the real API and renders the result + scope panel + confidence + OOD flags.
- [ ] `/evaluate` shows our MAPE vs baseline with pass/fail.
- [ ] Outbound staging POST fires (or is honestly shown as `skipped` when creds absent).

**Quality gates:**
- [ ] `scripts/verify.sh` green across both stacks (Rubocop + RSpec for Rails; ruff + mypy + pytest for Python).
- [ ] `scripts/secret_guard.sh` green — no key material in git or the deploy bundle.

---

## Open questions (only things that genuinely affect the build; resolved with the dataset or Claudio)

1. **Real-vs-augmented row split.** Real-only MAPE (~27 rows, baseline 40%) requires knowing
   which priced rows are *real jobs* vs *augmented*. The prep notes say sparse categories were
   "augmented" and Handyman "sampled down," so some rows are synthetic. **Resolution plan:** on
   dataset arrival, look for an explicit flag column; if none, derive the real subset by the
   rows whose pricing/description pattern matches genuine jobs (and cross-check the count lands
   near 27). If still ambiguous, this is a question for Claudio — flagged, not guessed.
2. **Staging endpoint auth.** Real outbound POST needs the `pro.houseparty.dev` booking URL +
   token. **Resolution plan:** build against a configurable stub; wire real creds if provided.
3. **Endpoint path on Rails.** Appendix A's path `/.netlify/functions/pricing-estimate` is
   Netlify-specific. **Decision (not a blocker):** expose `POST /pricing-estimate` on Rails
   (same resource name, no Netlify prefix since we're not on Netlify) and document it; optionally
   alias the literal Netlify path for drop-in compatibility. The evaluator is given our URL.

If this list is empty by Phase 4 it will say so; #1 is the only one that can affect the score.
