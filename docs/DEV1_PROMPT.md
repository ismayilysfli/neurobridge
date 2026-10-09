# COPY TO DEVELOPER 1 CODEX

You own **backend/**, **tests/test_economy.py**, and **tests/test_http.py**. Do not modify agent/ or frontend/. Your task is to make the independently testable game-economy simulator reliable and give Developer 2 a stable public API. Read docs/CONTRACT.md and preserve it; coordinate before modifying its schema.

1. Run `python -m pytest -q` and inspect current backend code. Confirm 3 variants (secure, reward_reset, upgrade_resale) and their independent deterministic oracle results.
2. Add robust input validation, session limits, error handling, reproducible reset and more unit tests for action constraints. Actions should always return observable state; invalid actions must not mutate state.
3. Add at least one **new** seeded economy configuration with a nontrivial economic failure that isn't simply `claim_reward` twice and with independent secure version. Coordinate the variant name with Developer 2 for operator UI only. Do not expose the exact bug or oracle to the AI.
4. Add a deterministic **random action baseline**, with fixed seeds and equal max-action budgets to the LLM. Its source and evaluation must be separate from the LLM agent. Report success/failure and number of steps per scenario.
5. Produce reproducible test results in `reports/` as JSON or CSV. Do not fabricate result numbers; do not claim any AI model was run by backend tests.
6. Integrate with Developer 2 before 17:30 and prioritize the demo. Testing should happen in an isolated authorized sandbox only.

Success criteria: all tests pass, two exploit types are independently verifiable, corrected scenarios produce no false violation, and API responses strictly match contract. Favor reliability over new features.
