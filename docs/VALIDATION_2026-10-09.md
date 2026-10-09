# Follow-up AI validation — 2026-10-09

Work was performed on `feat/ai-validation`, starting from `b2dd5eb`, on Windows with Python 3.14. The backend and API contract were not changed or inspected for exploit solutions. No independent held-out implementation was supplied.

## What the existing implementation already does correctly

`runner.py` validates model-selected actions against public schemas, accounts for rejected actions and model retries, preserves partial traces, and accepts findings only from backend `new_violations`. Replay executes the full recorded sequence in a fresh session and matches the rule identity. Secure control is a sequence-specific regression check. The original 49 tests passed after installing the declared dependencies.

The earlier campaigns retain real reward/trading discoveries and unsuccessful runs. Flash-Lite daily quota failures and Flash transient 429 responses materially truncated exploration. The recorded Flash trading run `5d5bdebc` spent two of five executed actions on rejected reward claims. Its prompts already contained accurate state snapshots: missing backend feedback was not the cause. The second rejection followed a profile change without any eligibility change.

## Fresh measurements

The checkout has no `.env`, Streamlit secrets, or `LLM_*` environment settings. The existing public deployment did have model configuration, so fresh browser sessions exercised its real Gemini 3.1 Flash-Lite client. No credentials were extracted, fabricated, or used as placeholders.

Each run allowed six actions, seven model HTTP calls, and 120 seconds. The deployment reported temperature 0.3, 1024 output tokens, minimal reasoning effort, and 6.5-second request spacing. Sixteen real model calls completed across three sequential runs, without provider errors or invalid model outputs.

| Scenario | Actions / calls | Finding | Runtime |
| --- | --- | --- | --- |
| Reward | 6 / 6 | None; budget exhausted | 41.74 s |
| Trading | 4 / 4 | Backend-verified and reproduced | 21.09 s |
| Secure control | 6 / 6 | None; budget exhausted | 48.11 s |

The reward run's final action changed eligibility but left no action budget to test the consequence. This is a real unsuccessful discovery run, not a verified finding. The trading finding is supported by its actual backend action response and automatic fresh-session replay. Auditing all three exported prompt histories found no hidden scenario names or verifier evidence.

The comparison in `reports/browser_comparison_93ef1ac4d2d6/comparison.json` invokes the existing `agent.evaluation` random baseline with six actions per run and new recorded seeds. The baseline found nothing in these three samples. AI ran on the public host; baseline ran on the local host. Before comparing, local replay matched every observed state transition, acceptance/rejection outcome, and expected violation, and the public specs matched. This is limited observed parity, not proof of identical hidden implementations. Do not combine this sample silently with the original campaign denominator or claim superiority.

## Focused changes and their limits

- `agent/prompts.py`: Summarize changes to allowed public fields and list untried public actions; reapply state filtering to historical observations. Generic instructions emphasize unchanged prerequisites, interaction coverage, and preserving enough action budget to follow up state changes. No action sequence, scenario label, or verifier implementation is supplied.
- `frontend/app.py`: Show other observed changes, including reward eligibility, in each timeline entry. Previously the timeline emphasized only coins and inventory.
- `scripts/compare_browser_runs.py`: Reuse the existing baseline and replay harness for downloaded real runs, retain source provenance, and require observed deployment/local parity. This is an experiment utility, not a second exploration engine.

The diagnosing-bugs workflow guided reproduction of environment/browser failures and the regression checks. The two new observation tests failed before the change and passed after it; all 51 tests passed afterward. These tests establish software behavior only. **The revised local prompt has not been tested with a real model and was not deployed.** The fresh public results use the original prompt, as recorded in each download.

## Failures retained

Initial test collection failed because Streamlit was missing. A subsequent run passed 45 tests but failed one fixture because the default temporary directory was inaccessible; specifying a workspace `--basetemp` resolved that. Dependency installation initially hit the sandbox network restriction and then succeeded with approved network access.

The final test run has one non-fatal Starlette deprecation warning. No model/provider failure occurred in the three fresh public runs; earlier provider failures remain preserved in the original campaign reports.

## Demo setup and handoff

The existing public URL was verified in fresh Chrome sessions:

https://ringtones-survive-kelkoo-inform.trycloudflare.com

It serves the existing deployment, not this modified Windows checkout. Keep its owner’s app/backend/tunnel processes running. Public checks covered real AI exploration, action history, automatic finding replay, explicitly recorded evidence, replay/control buttons, and parsed JSON downloads. The temporary URL is not durable hosting.

For local operation in PowerShell:

```powershell
.venv/Scripts/python.exe -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

Open `http://127.0.0.1:8501`. The app starts the loopback backend. Local replay/control/export work without a model key. To enable live local discovery, copy `.env.example` to ignored `.env`, configure your actual Gemini key locally, and restart Streamlit. Never paste the key into a report or commit it. No new backend API is needed, so there is no API change to coordinate with the economy developer.

Verification commands (choose a new temporary-test directory for a new run):

```powershell
.venv/Scripts/python.exe -m pytest -q --basetemp=.pytest_cache/validation-next
# Only after configuring local inference; consumes real provider quota:
.venv/Scripts/python.exe -u -m agent.evaluation --trials 1 --max-steps 6 --max-llm-calls 7 --timeout 120 --seed 2026100910
```

The existing evaluation command writes latest aggregate files and RESULTS.md; retain versioned campaigns and this follow-up document when refreshing summaries. Preserve errors and exhausted runs. For the UI comparison already executed:

```powershell
.venv/Scripts/python.exe scripts/compare_browser_runs.py reports/browser_05f52ec83457/browser_live_download.json reports/browser_55ed3e3c7f2d/browser_live_download.json reports/browser_dbbd59dc27b5/browser_live_download.json
```

For judging, show a fresh run only when it actually executes. If inference is unavailable, load an explicitly labeled recorded real run and demonstrate live replay/control. Neither replay nor a screenshot counts as a new AI discovery. Remaining work is local model validation of the prompt revision, an independent held-out scenario if supplied, and deployment of the revision only after validation.
