# Build Log — HouseAccount AI Pricing Model

One line per meaningful decision or phase transition. This is the running record
the skill keeps so the human can follow along without being interrupted.

## Foundation
- Fresh build in `HouseAccout_pricing/`. Per explicit user instruction, the sibling
  `houseAccount/` folder is OFF-LIMITS — no code, data, docs, or models drawn from it.
- Source of truth: the PRD (`prd.md`, also pasted at kickoff). Appendix A is the API contract.
- Preflight: green except the app AI key (collected at intake). gh=robin-raq, Railway+Vercel, Playwright 1.60, ffmpeg 8.
- Decision — **API stack: Rails API + Python model service** (user choice). Rails owns the Appendix A
  contract (auth, validation, error shapes, outbound staging POST); Python service owns features→model→intervals→confidence.
- Decision — **Model: Hybrid** (user choice). Deterministic gradient-boosted ML core + conformal
  prediction intervals as the backbone; LLM scope-extraction from `job_description` layered on
  (temp 0, cached, deterministic fallback) so eval reproducibility and the <2s SLA stay protected.
- Toolchain — Ruby 3.4.7 + Rails 8.1.3 via rbenv (shims at `$HOME/.rbenv/shims`; non-login shells must prepend it to PATH);
  Python via uv; Node 22; ffmpeg 8; Playwright 1.60.
- Deploy target — Railway (best fit for a long-running Python service + a Rails web service; both present & authed-check pending).
- Outward-facing actions (first public push under `robin-raq`, deploy) will pause for explicit user go-ahead.
- Awaiting from user: `data/raw/houseaccount_pricing_sample.csv` (Sheet needs their Google auth) and `OPENAI_API_KEY`.

## Phase 1 — Expand the PRD
- Wrote `docs/PRD-expanded.md`. Disambiguated the two endpoints (inbound Appendix-A `pricing-estimate`
  we expose vs outbound `bookings-create` staging POST). Locked a 4-screen demo inventory
  (Estimate Sandbox, Evaluation, Model Card, API & Integration). Defined the runtime AI surface
  (LLM scope-extraction, temp 0, cached, deterministic fallback; ML core self-sufficient).
- Open question #1 (the only score-affecting one): how real vs augmented rows are split for the
  real-only MAPE (~27 rows). Resolution deferred to dataset arrival; flagged, not guessed.

## Phase 2 — Capture style
- Worker captured houseaccount.com (apex resolved; home/providers/about, all HTTP 200, measured not inferred).
- Tokens: navy `#143c55`, blue `#2d62ff`, amber CTA `#ffb959`; 8px cards, 100px pills, soft navy shadows;
  font Circularxx (proprietary). Wrote `design/style-guide.md`, `design/tokens.json`, 3 reference PNGs.
- PNGs gitignored (`design/*.png`) — references, ~6MB, kept local not shipped.

## Phase 3 — UI mockup
- Built single-file `ui/mockup.html` (inline CSS/JS, Google-Fonts Mulish w/ Arial fallback). 4 screens:
  Estimate Sandbox (hero), Evaluation, Model Card, API & Integration. All nav wired; OOD example shows
  confidence forced <0.5 + "passed through, not rejected".
- Deliberate styling choice: used **Mulish** for the Circular substitute (rounder, closer match) vs the
  guide's Inter suggestion. Noted, not a conflict.
- Verified headless (`scripts/verify_mockup.mjs`): all 4 screens activate, **0 console errors**.

## Phase 4 — Build, ship, verify
- Stack layout: `api/` (Rails 8 API-only, Appendix-A contract) + `model_service/` (Python FastAPI: features→model→intervals→confidence).
- BLOCKER for the *model*: need `data/raw/houseaccount_pricing_sample.csv`. BLOCKER for *runtime LLM + deploy + video*: need `OPENAI_API_KEY`.
- Proceeding with data-independent scaffold (Rails contract + gates + Python skeleton w/ stub estimator) while awaiting inputs.
- Rails 8 API-only (no DB; estimates are pure request/response). Python via uv, FastAPI model service.
- Python core DONE+green: categories, confidence/OOD, scope (fallback + optional LLM), schemas, estimator (stub behind PricingModel protocol), FastAPI /predict + /health. 35 tests, ruff+mypy clean.
- Rails contract DONE+green: bearer auth (secure_compare), required-field 400s, malformed-JSON 400, 405, wrapped 200; ModelServiceClient. 6 request specs; rubocop pinned to STYLE.md (100-char, outdented private).
- `scripts/verify.sh` (both stacks) GREEN; `secret_guard.sh` clean. Restored `api/.gitignore` (rails --skip-git omitted it) so master.key stays untracked.
- 4 local commits (scaffold/meta, model service, api contract, tooling). NOT pushed (awaiting go-ahead).
- `.env` scaffolded untracked: generated GAUNTLET_PRICING_SECRET; OPENAI_API_KEY placeholder for user to fill. `.env.example` committed.
- CHECKPOINT — blocked on two user inputs: (1) dataset CSV at `data/raw/houseaccount_pricing_sample.csv`
  for model training + MAPE; (2) real OPENAI_API_KEY in `.env` for runtime LLM + deploy + demo video.

## Phase 4 (cont.) — Dataset received, EDA, modeling
- Inputs verified: CSV 1431 data rows / 11 PRD columns; OPENAI_API_KEY present (sk-, 164 chars, value never printed).
- EDA: baseline reproduced exactly — blended MAPE 11.56% / median APE 8.33% on 411 priced rows. Confirms eval math.
- **Open question #1 RESOLVED (non-circular):** real jobs = priced rows with globally-unique job_description =
  **31 rows, baseline 35.9%** (~ PRD's 27 @ ~40%). Augmented rows reuse description templates (freq>=2). Real rows
  cluster in label-starved production cats (Handyman 14 @48%, Plumbing 3, Electrical 2, Flooring 4).
- Data quirks: deadline has 7 variants + nulls (must canonicalize to the 4); priced subset is engineered
  (5 cats at 65-66 rows each); production verticals are label-starved (Plumbing 3 priced, Electrical 2).
- Modeling decision: **correction model on top of original_estimate** (prior as feature + scope/zip/subtype to
  learn residuals). Eval via **grouped CV by description template** to stop augmentation leakage.
- Fixed a real bug: pandas `category` codes differed train vs test/serve → froze a category vocabulary
  (learn_categories/align_categoricals) so codes align everywhere. (Numbers unchanged → categoricals low-signal.)
- Added `is_augmented` provenance feature: model corrects unique/real rows, leaves templated rows near prior.
  Bake-off (10 configs x 5 seeded grouped-CV): winner **verycons+weight+shrink0.7** = blended **10.86%±0.14**,
  real **30.43%±1.11** (vs baselines 11.56 / 35.87) — beats both robustly.
- LLM-scope ablation (98 descriptions extracted via gpt-4o-mini): LLM scope features improve real-only
  **30.43→29.86** (lower variance), blended unchanged. Deterministic scope alone also beats both bars.
- DECISION: ship **LLM-scope model** (verycons+weight+shrink0.7) with deterministic scope as tested fallback;
  report both numbers. Honors the hybrid; deterministic core is the robustness guarantee.
