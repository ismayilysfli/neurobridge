# Executed acceptance checks

- Backend health and public specification: successful actual HTTP requests.
- Real model connection and validated action: Gemini 2.5 Flash-Lite, Gemini 2.5 Flash, and Gemini 3.1 Flash-Lite each selected and executed a real action. Saved connectivity probes are separate from benchmark denominators.
- Multistep exploration: actual reward and trading runs; model hypotheses, prompts, API responses and state transitions saved.
- Budgets and failures: all saved runs obey action/model-call limits; automated tests cover timeout, invalid outputs, rejected actions, missing configuration, session failure and provider failure.
- Prompt privacy: tests check that actual fixture names and verifier codes are absent. The agent never imports backend internals.
- Backend verification and exact replay: reward and trading findings genuinely reproduced in fresh sessions. Every saved finding has backend evidence. Regression checks execute the same full sequence against secure control.
- Dashboard: fresh public Chrome session rendered rules/status and executed a real model-selected action. Replay/control buttons made actual HTTP requests. JSON downloads were parsed and checked. Saved traces are explicitly labeled recorded evidence.
- Automated tests: 49 passing tests, including the unchanged original backend tests and new agent/replay/UI tests. Scripted models are software tests, not AI effectiveness evidence.
- Evaluation: 30 measured AI/random runs across three campaigns, preserving failures and distinct budgets. Repeated baseline seeds across the first two campaigns are disclosed as replication rather than extra independent samples. No superiority claim.
- Single-deployment helper: cold-start health/action test and duplicate-process prevention passed on an available loopback port. An earlier attempt on occupied port 8001 failed visibly; the service using that port was not modified.
- Backend preservation: five original backend/test files match the starter ZIP byte-for-byte. Integrity hashes are saved.
- Credentials: local key lives in ignored .env with mode 0600. Source, docs, tests, scripts and JSON/CSV reports were checked for its absence. Distribution excludes secrets and virtual environment.
- Demo access: the temporary public Cloudflare URL was checked in a fresh browser. Keep the host, dashboard, sandbox and tunnel running. Durable hosting, another-device validation, and a permanent URL are not claimed.

Evidence: `reports/deployment.json`, `reports/local_startup.json`, `reports/backend_integrity.json`, `reports/implementation_checks.json`, individual run reports, and `docs/RESULTS.md`.

## Remaining external limitations

No independent held-out backend scenario was supplied. No remote Streamlit hosting account was provisioned or verified. The starter's hackathon eligibility and official build-period/disclosure rules require checking the actual competition rules. A two-minute demo script is provided; no completed pitch deck or narrated demo video is claimed. Free inference quotas can interrupt future runs; the recorded genuine findings still support live local replay and regression without a model call.
