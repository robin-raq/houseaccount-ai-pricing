# Test Results — HouseAccount AI Pricing Model

## Model accuracy (grouped CV by description, 5 seeds, leakage-free)

| Metric | Baseline | Ours (shipped, LLM scope) | Verdict | Deterministic fallback |
|---|---|---|---|---|
| Blended MAPE (411 priced) | 11.56% | **10.92%** | PASS | 10.9% |
| Real-only MAPE (31 real jobs) | 35.87% | **31.08%** | PASS | 31.22% |

Baselines per brief: blended 11.6%, real-only ~40%. Real jobs are priced rows with a
globally-unique `job_description` (augmented rows reuse templates). Both the shipped
model and the deterministic-only fallback beat both baselines.

_Regenerate: `make train` (model accuracy) and `make verify` (code gates)._

## Code quality gates (`scripts/verify.sh`)

```
    [PASS]
    [PASS]
    [PASS]
    [PASS]
    [PASS]
    [PASS]
RESULT: ALL GREEN — every advertised quality gate passed.
```
