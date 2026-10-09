# Measured evaluation results

## Follow-up validation, 2026-10-09 18:43–18:50 Asia/Baku

Three fresh public-browser Gemini 3.1 Flash-Lite runs used **6 attempted actions, 7 model calls, and 120 seconds** each. There were 16 actual model calls total, zero provider errors, and zero invalid model outputs. The deployed original prompt was used; the local prompt revision is **not model-validated**.

| Environment | AI finding / actions | Seeded random finding / actions | AI outcome |
| --- | --- | --- | --- |
| reward_reset | No / 6 | No / 6 | Action budget exhausted; eligibility changed on the final action |
| upgrade_resale | Yes, reproduced / 4 | No / 6 | Backend-verified finding, automatically replayed |
| secure | No / 6 | No / 6 | Action budget exhausted |

Random seeds were 2026100901, 2026100902, and 2026100903, respectively. This comparison reuses `agent.evaluation.random_baseline` and its summary/replay functions. The AI ran on the existing public deployment; the baseline ran against local HTTP. Public specs and all recorded actions' before/after states and acceptance outcomes matched in local replay, including the trading violation. That check does not prove hidden implementation parity. These six rows remain separate from the original same-deployment campaigns below; one trial per environment does not establish superiority. The fresh trading sequence also produced `NO_VIOLATION_OBSERVED` in a local secure-control session.

Evidence: [comparison and seeds](../reports/browser_comparison_93ef1ac4d2d6/comparison.json), [reward run](../reports/browser_05f52ec83457/browser_live_download.json), [trading run](../reports/browser_55ed3e3c7f2d/browser_live_download.json), [secure run](../reports/browser_dbbd59dc27b5/browser_live_download.json). [Validation notes](VALIDATION_2026-10-09.md) explain changes, failures, and demo setup. All previous reports and campaign results remain unchanged.

## Original campaign results (preserved)

Generated: 2026-10-09T13:32:15.634310+00:00. All completed campaigns, including failures, are listed below.

Environments: Merchant Town owned sandbox; `reward_reset`, `upgrade_resale`, and `secure`. All runs create fresh sessions. Scenario labels, backend source and verifier evidence are withheld from the model. The model receives only public rules/schemas and actual observations.

Random baseline: uniform random among actions with observable reward eligibility, inventory and affordability; schema-valid seeded parameters; no ordered sequences. Rejected API actions count toward the same game-action budget as the AI. Baseline code is a temporary public-API evaluation adapter because no teammate baseline was present.

## Campaign de56a0c42dc4

Model: `gemini-2.5-flash-lite`. Trials per environment per method: 2. Budget: 12 game actions, 15 model HTTP calls, 120 seconds. Retries and invalid outputs consume the model budget. Replay/regression do not count as additional discoveries.

| Method | Environment | Trials | Verified | Reproduced | Mean actions | Mean runtime (s) | Provider errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| real_llm | reward_reset | 2 | 1 | 1 | 3.0 | 5.94 | 3 |
| real_llm | upgrade_resale | 2 | 1 | 1 | 2.5 | 6.83 | 5 |
| real_llm | secure | 2 | 0 | 0 | 0.5 | 4.57 | 6 |
| seeded_state_aware_random | reward_reset | 2 | 2 | 2 | 7.0 | 0.01 | 0 |
| seeded_state_aware_random | upgrade_resale | 2 | 1 | 1 | 10.5 | 0.02 | 0 |
| seeded_state_aware_random | secure | 2 | 0 | 0 | 12.0 | 0.03 | 0 |

Failures/exhausted runs:

- `real_llm` / `secure` / trial 1: `PROVIDER_FAILURE`, 1 actions, 4 model calls, 0 rejected actions, 0 invalid model outputs.
- `seeded_state_aware_random` / `secure` / trial 1: `ACTION_BUDGET_EXHAUSTED`, 12 actions, 0 model calls, 2 rejected actions, 0 invalid model outputs.
- `real_llm` / `reward_reset` / trial 2: `PROVIDER_FAILURE`, 0 actions, 3 model calls, 0 rejected actions, 0 invalid model outputs.
- `real_llm` / `upgrade_resale` / trial 2: `PROVIDER_FAILURE`, 1 actions, 6 model calls, 0 rejected actions, 0 invalid model outputs.
- `seeded_state_aware_random` / `upgrade_resale` / trial 2: `ACTION_BUDGET_EXHAUSTED`, 12 actions, 0 model calls, 8 rejected actions, 0 invalid model outputs.
- `real_llm` / `secure` / trial 2: `PROVIDER_FAILURE`, 0 actions, 3 model calls, 0 rejected actions, 0 invalid model outputs.
- `seeded_state_aware_random` / `secure` / trial 2: `ACTION_BUDGET_EXHAUSTED`, 12 actions, 0 model calls, 2 rejected actions, 0 invalid model outputs.
## Campaign 9dfb6734bfff

Model: `gemini-2.5-flash-lite`. Trials per environment per method: 2. Budget: 12 game actions, 15 model HTTP calls, 120 seconds. Retries and invalid outputs consume the model budget. Replay/regression do not count as additional discoveries.

| Method | Environment | Trials | Verified | Reproduced | Mean actions | Mean runtime (s) | Provider errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| real_llm | reward_reset | 2 | 0 | 0 | 0.0 | 16.42 | 6 |
| real_llm | upgrade_resale | 2 | 0 | 0 | 0.0 | 19.48 | 6 |
| real_llm | secure | 2 | 0 | 0 | 0.0 | 19.46 | 6 |
| seeded_state_aware_random | reward_reset | 2 | 2 | 2 | 7.0 | 0.01 | 0 |
| seeded_state_aware_random | upgrade_resale | 2 | 1 | 1 | 10.5 | 0.02 | 0 |
| seeded_state_aware_random | secure | 2 | 0 | 0 | 12.0 | 0.02 | 0 |

Failures/exhausted runs:

- `real_llm` / `reward_reset` / trial 1: `PROVIDER_FAILURE`, 0 actions, 3 model calls, 0 rejected actions, 0 invalid model outputs.
- `real_llm` / `upgrade_resale` / trial 1: `PROVIDER_FAILURE`, 0 actions, 3 model calls, 0 rejected actions, 0 invalid model outputs.
- `real_llm` / `secure` / trial 1: `PROVIDER_FAILURE`, 0 actions, 3 model calls, 0 rejected actions, 0 invalid model outputs.
- `seeded_state_aware_random` / `secure` / trial 1: `ACTION_BUDGET_EXHAUSTED`, 12 actions, 0 model calls, 2 rejected actions, 0 invalid model outputs.
- `real_llm` / `reward_reset` / trial 2: `PROVIDER_FAILURE`, 0 actions, 3 model calls, 0 rejected actions, 0 invalid model outputs.
- `real_llm` / `upgrade_resale` / trial 2: `PROVIDER_FAILURE`, 0 actions, 3 model calls, 0 rejected actions, 0 invalid model outputs.
- `seeded_state_aware_random` / `upgrade_resale` / trial 2: `ACTION_BUDGET_EXHAUSTED`, 12 actions, 0 model calls, 8 rejected actions, 0 invalid model outputs.
- `real_llm` / `secure` / trial 2: `PROVIDER_FAILURE`, 0 actions, 3 model calls, 0 rejected actions, 0 invalid model outputs.
- `seeded_state_aware_random` / `secure` / trial 2: `ACTION_BUDGET_EXHAUSTED`, 12 actions, 0 model calls, 2 rejected actions, 0 invalid model outputs.
## Campaign 33c6cbe44440

Model: `gemini-2.5-flash`. Trials per environment per method: 1. Budget: 6 game actions, 7 model HTTP calls, 120.0 seconds. Retries and invalid outputs consume the model budget. Replay/regression do not count as additional discoveries.

| Method | Environment | Trials | Verified | Reproduced | Mean actions | Mean runtime (s) | Provider errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| real_llm | reward_reset | 1 | 1 | 1 | 4.0 | 20.52 | 0 |
| real_llm | upgrade_resale | 1 | 0 | 0 | 5.0 | 93.26 | 2 |
| real_llm | secure | 1 | 0 | 0 | 6.0 | 38.97 | 0 |
| seeded_state_aware_random | reward_reset | 1 | 1 | 1 | 5.0 | 0.01 | 0 |
| seeded_state_aware_random | upgrade_resale | 1 | 0 | 0 | 6.0 | 0.01 | 0 |
| seeded_state_aware_random | secure | 1 | 0 | 0 | 6.0 | 0.02 | 0 |

Failures/exhausted runs:

- `real_llm` / `upgrade_resale` / trial 1: `MODEL_BUDGET_EXHAUSTED`, 5 actions, 7 model calls, 2 rejected actions, 0 invalid model outputs.
- `seeded_state_aware_random` / `upgrade_resale` / trial 1: `ACTION_BUDGET_EXHAUSTED`, 6 actions, 0 model calls, 2 rejected actions, 0 invalid model outputs.
- `real_llm` / `secure` / trial 1: `ACTION_BUDGET_EXHAUSTED`, 6 actions, 6 model calls, 2 rejected actions, 0 invalid model outputs.
- `seeded_state_aware_random` / `secure` / trial 1: `ACTION_BUDGET_EXHAUSTED`, 6 actions, 0 model calls, 1 rejected actions, 0 invalid model outputs.

## Interpretation and limitations

The benchmark question is whether AI-guided exploration beats a simple unguided tester under the same action budget. These measurements do not establish that it does: the random baseline also finds defects, the sample is very small, and quota interruptions make several AI runs incomplete. Compare methods within a campaign, not across different budgets/models. Repeated baseline seeds in the first two campaigns are replication checks, not additional independent samples.

Flash-Lite reached this account's daily free-tier limit. A diagnostic 429 response reported 20 requests per model per day and a retry delay longer than the entire exploration budget. Those incomplete runs stay recorded. Request pacing cannot recover exhausted daily quota. Gemini 2.5 Flash was independently probed and executed a real action; later experiments record its exact identity.

No model hypothesis is a confirmed finding without backend verification. Secure-scenario verified flags are visible in JSON/CSV and must be investigated; a failure or negative result never proves the game secure. A regression check establishes only that the recorded sequence did not trigger a verifier rule in that secure session. No confirmed false finding was manufactured; nonreproducing findings would remain FAILED_REPLAY. Unit/UI tests use labeled mocked models and are excluded from these measurements.

Only two deliberately defective toy configurations and one secure control are available. No independent held-out backend scenario was supplied. No commercial-game integration, statistical significance, cost/savings estimate, or generalization claim is supported. Cost not measured.

The single-action connectivity probe, initial standalone reward discovery, and public-browser single-action test are saved separately. They are not silently included in the matched benchmark denominators. Individual reports include exact actions/responses, model prompts, measured latency and provider token usage. Original versioned campaign JSON/CSV are retained.
