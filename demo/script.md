<!--
Demo Video Script — HouseAccount AI Pricing Model. Target runtime ~5:00-5:30.
Each ### heading is a beat (dropped by tts.py); the paragraph under it is the spoken
narration. Record a matching screen capture per beat into demo/clips/clip_00N.mp4.
-->

### Beat 1 — The problem (Estimate screen)

HouseAccount connects homeowners with home-service pros. And the moment that makes or breaks the match is the price. If the homeowner trusts the price, they book without shopping around. If the provider trusts it, they accept without renegotiating. So we built a pricing engine to earn that trust: a model that's accurate, honest about its own uncertainty, and fast enough to run the instant a booking comes in. Let me show you how it works, and then prove that it beats the model HouseAccount uses today.

### Beat 2 — A live estimate (click the Water heater example)

Here's a real booking, in the homeowner's own words: a fifty-gallon gas water heater, the pilot won't stay lit, needs replacing. I click Get estimate, and in about a second, we have a price. A range from roughly fourteen hundred to seventeen-fifty, a point estimate near sixteen hundred, and the important part: a confidence of point eight-six. Now look at the panel called "what the model saw." The engine read that free-text description with a language model and pulled out structured scope: it's a fifty-gallon unit, standard materials, the customer isn't supplying the parts. That's scope a simple keyword matcher would miss completely. And it's exactly what lets the model price a job it has almost no direct training examples of. And notice the speed. That entire round trip, reading the description, extracting the scope, pricing the job, and calibrating the confidence, came back in about a second, comfortably under the two-second budget the booking flow needs.

### Beat 3 — Honest about uncertainty (click the Whole-home remodel example)

But a good estimate knows when it's guessing. Watch what happens with a whole-home remodel, a six-figure job in a category we don't sell in production. The confidence collapses below point five, and the engine tells you exactly why: the price is over five thousand dollars, the prediction interval is unusually wide, and the category is outside our production set. Crucially, it does not reject the job. It still prices it, and flags it, so the marketplace can route it to a human instead of auto-booking. That's the whole difference between a number, and a number you can actually trust.

### Beat 4 — Does it beat the baseline (Evaluation tab)

So is it actually better than what HouseAccount has today? These are live numbers, measured by cross-validation. We're graded on two error rates. On the full set of priced jobs, we're at ten-point-nine percent error, versus the eleven-point-six baseline. And on the real jobs, the genuinely hard one-off requests, we cut the error to around thirty-one percent, down from a baseline near forty. We beat both, and the real-job win is the one that matters most. The story is in this table. The biggest win is Handyman: thirty-four percent error versus forty-eight for the baseline.

### Beat 5 — The insight (stay on Evaluation)

That win is not an accident, and it's the insight that shaped the whole model. This training data is a mix. Most of the priced jobs are augmented templates, where the old estimate is already accurate. But buried inside are the genuine, one-off jobs, and we found them with a signal that has nothing to do with price: a description that appears only once in the whole dataset. Those real jobs are hard, they're concentrated in label-starved categories like Handyman and Plumbing, and they are exactly the jobs we optimized to win, because they're the ones a homeowner actually books.

### Beat 6 — How it works (Model Card tab)

Here's the mechanism. A naive model would just relearn the old estimate and add noise; it would tie the baseline and never beat it. So instead of pricing from scratch, our model predicts the correction to the previous estimate, using the signals the old model ignored: the scope from the description, the region, the job type. The correction is near zero where the prior is already right, and meaningful where it isn't. The confidence intervals come from conformal prediction, scaled by how uncertain the previous model was, so harder jobs honestly read as less certain.

### Beat 7 — Why the numbers are honest (stay on Model Card)

And these numbers are honest, which matters as much as the numbers themselves. Because those augmented templates repeat across the data, a careless evaluation would leak answers from training straight into the test set and inflate the score. We group every cross-validation fold by description to prevent exactly that. Both the Rails and the Python sides are covered by tests and linters that run on every change. And the model beats the baseline even with the language model switched off, so accuracy never hard-depends on an outside API being reachable.

### Beat 8 — The contract and integration (API tab)

Finally, this has to plug into HouseAccount's booking flow. The engine is a Rails service that implements the exact API contract: bearer authentication, a structured booking in, a structured estimate out. I'll run the live endpoint. Two hundred OK, and there's the estimate. The contract also handles the unhappy paths exactly as specified: a missing required field, a bad token, or the wrong method each returns the precise error the booking system expects. Every priced booking is also posted back into the booking flow and logged right here. Under the hood it's two clean layers: Rails owns the contract, a Python service owns the model, so each one is tested on its own.

### Beat 9 — Close

So: a pricing engine that beats the baseline on both the easy jobs and the hard ones, tells you honestly when it's unsure, runs in under two seconds, and drops straight into the booking flow. Built to earn the one thing a marketplace really runs on: trust. Thanks for watching.
