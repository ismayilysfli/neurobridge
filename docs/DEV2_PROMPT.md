# COPY TO DEVELOPER 2 CODEX

You own **agent/**, **frontend/**, and **tests/test_agent.py** (to create). Do not modify backend/. Follow docs/CONTRACT.md exactly and use agent/client.py for HTTP; you can mock API calls until Developer 1 brings up the server.

Build an autonomous exploratory **AI agent** for the owned game-economy sandbox. The model receives only GET /api/spec and a player's observable state/action feedback, never source files, hidden variant identities, expected exploit sequences, or oracle internals. Do not hardcode exploit sequences or leak fixture names into prompts.

1. Implement `explore(client, max_steps=15)` in agent/runner.py using an OpenAI-compatible REST API configured through `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. Never commit keys. Give model a concise system instruction: propose a legal game action to test for a violation of public rules; output strict JSON `{ "action": ..., "params": ..., "reason": ... }`. Validate action name and parameters before performing it. Handle non-JSON responses, retries, malformed actions and HTTP failures. Include hard bounds on agent steps, calls, time and tokens.
2. Record every request choice, action, result, model latency and relevant token usage. The oracle may report a verified violation through `new_violations`; only then mark `verified=true`. Preserve exact replay steps and run them in a new session to ensure repeatability; distinguish original discovery from replay.
3. Extend frontend/app.py: operator-selectable scenario (never included in agent prompt), model/env status, Start AI Test, progress/action timeline, rule evidence, Export JSON, fixed-version rerun demonstration, and results summary. UI must not falsely say 'AI discovered' when no model was called.
4. Create `tests/test_agent.py` with mocked LLM responses to test JSON/schema handling, invalid tool calls, step-budget limit, and transcript collection. Mock tests do NOT establish live AI effectiveness.
5. Do a genuine live-model dry run with no leak of source/internal scenario identifiers to the LLM. Record successes **and failures**, and compare against Developer 1's random-action baseline under comparable action budgets. Summarize metrics for the pitch.

Stop new feature work by 18:15. Ensure judge-accessible demo, reliable live scenario, replay evidence, and 2-minute recording by 19:30.
