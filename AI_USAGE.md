# AI Usage Log

## Tools used

- **Claude Code (Claude Opus 4.8)** — the primary agent. It drove a PRD-to-product workflow:
  expanding the PRD, capturing the client's visual style, building a UI mockup, doing the data
  analysis and modeling, writing both services, and producing these docs. The human set
  direction and made the load-bearing decisions; the agent did the building and analysis.
- **A headless browser (Playwright)** — driven by the agent to capture HouseAccount's design
  tokens from the live site and to live-verify the running app (click through, trigger a real
  estimate, screenshot, assert no console errors).
- **OpenAI `gpt-4o-mini`** — the *runtime* model inside the product, used for scope extraction
  from job descriptions (temperature 0, cached). This is the "AI" the deployed app calls; it is
  separate from the agent that built the project.

## Significant decisions & prompts that shaped the architecture

The human made four decisions that steered everything; the rest the agent worked out and
reported back.

1. **"Don't use the other folder."** An earlier attempt existed in a sibling directory; the human
   directed a clean-slate build from the PRD only. This kept the work honest and unentangled.
2. **Stack: Rails API + Python model service.** Asked to choose, the human picked Rails for the
   contract layer (the PRD's stated preference) with a Python service for the model. This split
   became the project's backbone — Rails owns auth/validation/error-shapes, Python owns the brain.
3. **Model: hybrid (ML core + LLM scope extraction).** The human chose to let an LLM read scope
   from the free-text descriptions, with the agent instructed to keep a deterministic core so the
   graded result wouldn't hard-depend on an API.
4. **The LLM scope-extraction system prompt** (in `pricing/llm_scope.py`): *"You convert a
   homeowner's free-text home-service request into structured scope signals used to price the job.
   Return a flat JSON object of string values only … Never include a price."* Constraining it to
   structured signals (not a price) is what keeps the LLM additive rather than authoritative.

The agent's own consequential calls, each grounded in the data:

5. **"How are real jobs distinguished from augmented ones?"** — the agent's EDA found the answer
   (globally-unique descriptions), which reframed the entire modeling problem.
6. **"Predict the correction, not the price."** — the residual-on-prior framing, chosen after the
   first from-scratch model failed the blended bar by adding noise to easy rows.
7. **"Beat it robustly, not on one lucky split."** — a 10-config × 5-seed bake-off selected for a
   robust margin rather than a single best number.

## Validation steps for AI-generated code

- **Two deterministic repo gates, enforced continuously:** `secret_guard.sh` (no key material in
  git or the build) and `verify.sh` (rubocop, rspec, ruff, mypy, pytest across both stacks), plus a
  one-time tool-presence preflight at the start. Every commit was green.
- **Tests-first for the contract and the core promise.** The Appendix A endpoint was built against
  a failing request spec; the "beats both baselines" claim is itself a test
  (`test_deterministic_model_beats_both_baselines`).
- **Leakage-free evaluation.** Cross-validation is grouped by description so the augmented
  templates can't leak train→test — the agent caught that a naive split would inflate the score.
- **Hallucination / bug catches the agent made on itself:**
  - A LightGBM + pandas `category` pitfall — category codes differed between train and serve,
    silently corrupting the categorical signal. Fixed by freezing a category vocabulary.
  - A confidence-calibration bug — a legitimate $1,800 job was wrongly flagged out-of-distribution
    because the OOD comparison used the model's own (tight) interval median instead of the
    dataset's observed range. Fixed, plus normalized conformal so confidence varies by difficulty.
  - The first model *failed* the blended bar (11.76% vs 11.56%); rather than ship it, the agent
    diagnosed why (noise on easy rows) and changed the approach.
- **Measured, not assumed.** Whether LLM scope features help was settled by an ablation, not a
  hunch — they improve the real bar by ~0.5pp, so they ship, with the deterministic fallback as
  the safety net.

## Reflection

**Where AI helped most.** The EDA-to-insight loop. The single most valuable move in the project —
identifying the real-vs-augmented split via description uniqueness — came from the agent poking at
the data, noticing the templated descriptions, and testing a non-circular hypothesis. That insight
reframed the whole model. AI was also strong at the unglamorous correctness work: catching the
categorical-encoding bug and the OOD calibration error, both of which would have shipped silently.

**Where it produced bad output.** The first model was wrong (it failed the blended bar), and the
first confidence calibration was wrong (spurious OOD flags). Neither was caught by "it runs" — both
needed an actual look at the numbers and the behavior. The lesson held throughout: a green boot is
not a correct result, which is exactly why the gates and the behavioral tests matter.

**What I'd do differently.** Spend even more of the budget up front on data understanding before
writing any model code — almost every modeling decision flowed from the EDA, and the one rework
(the from-scratch model) came from not fully internalizing the easy-vs-hard structure first. And
treat confidence calibration as its own testable surface from the start, rather than discovering
its bug in a smoke test.
