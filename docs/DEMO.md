# Two-minute demonstration

Use the live app or a clearly labeled saved real-model run. Never present a saved trace as a new live discovery. Quota failures are real results and should remain visible.

- **0:00–0:15:** Game economy logic can accidentally allow repeated rewards or currency creation. This tool tests explicit developer-supplied rules in an owned sandbox.
- **0:15–0:30:** Show public rules and action schemas. Explain that scenario names, source code, and verifier internals are withheld from the model.
- **0:30–1:10:** Select a controlled scenario and press START AI SECURITY TEST. Show the actual model hypotheses, API actions, state changes and budgets. If rate-limited, show the failure and select a labeled recorded real-model run.
- **1:10–1:30:** Show backend rule evidence and REPRODUCED status. Explain that a fresh session executes the full recorded sequence and must violate the same rule.
- **1:30–1:45:** Press RUN AGAINST SECURE CONTROL. Show actual responses, including rejected operations. This checks the recorded sequence only.
- **1:45–2:00:** Download JSON. Show measured AI/random results and failures. The small toy sample does not establish statistical superiority or real-game generalization.

## Slide-ready technical descriptions

**Problem:** Economy logic defects can break progression, rewards and virtual currency balances.

**Users:** Game developers and QA/security teams testing their own economies.

**Solution:** AI-guided adversarial testing for game economies with reproducible evidence.

**AI contribution:** A real Gemini model chooses each action from public schemas, observes actual results, and adapts its next hypothesis. No exploit sequences are embedded in the exploration agent.

**Architecture:** Streamlit → model-guided Python explorer → loopback FastAPI sandbox → deterministic rule verifier → fresh-session replay → secure-control regression. The inference layer uses OpenAI-compatible HTTP.

**Testing:** Scripted model doubles verify software behavior. Separate live-model runs use fresh sessions and fixed budgets. A seeded state-aware random baseline uses the same action budget. Reports retain failures.

**Results:** Use the exact current tables in RESULTS.md and reports/evaluation.json. The reward and trading defects have genuinely been discovered and reproduced by live Gemini runs; do not claim every trial succeeded.

**Feasibility:** Small Python application, free-tier inference, no model training, database, queue, or paid infrastructure requirement. Model quotas can interrupt a demo.

**Limitations:** Controlled toy economies only; explicit public invariants required; no commercial game integrations; small sample; provider quotas; negative runs do not prove security; temporary tunnel availability depends on running local processes.

**Future:** Adapter interfaces for authorized game test environments and richer public action schemas. No arbitrary external target scanning.

## Submission and disclosure

The extracted starter already supplied the FastAPI economy, intentionally defective fixtures, contract, and deterministic backend tests. New work supplies the agent, HTTP inference, replay, report/evaluation code, and Streamlit dashboard. Dependencies and pretrained Gemini inference are external components. Confirm official build-period eligibility yourself; no independent confirmation of hackathon rules was supplied. Screenshots, tests, and saved traces do not replace a live judge-accessible app or demo recording.
