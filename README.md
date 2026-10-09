# Game Economy Exploit Tester

AI-guided adversarial testing for owned game economies. A real language model chooses actions from public game rules and schemas, executes them through HTTP, and observes state changes. Only the backend verifier can confirm a rule violation; replay must reproduce the same rule in a fresh session. Secure-control checks apply to the recorded sequence only.

## Run locally

Python 3.10+ (tested on 3.12). From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Set LLM_API_KEY in .env. Never commit it.
python -m streamlit run frontend/app.py --server.address 127.0.0.1
```

The dashboard starts the existing FastAPI backend on `127.0.0.1:8000` when necessary. A lock and health check prevent duplicate starts on Linux. The model endpoint and key can instead come from Streamlit secrets. No external sandbox URL input is exposed.

For separate backend operation:

```bash
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
# Set AUTO_START_BACKEND=0 if desired.
```

Open http://127.0.0.1:8501. Select a controlled environment and press START AI SECURITY TEST. Findings trigger automatic replay. Replay/control buttons make actual new-session HTTP requests. Reports are saved as unique JSON snapshots in `reports/`, and can be downloaded.

## Model configuration

The configured demo and example use the verified `gemini-3.1-flash-lite` with Google's [OpenAI-compatible endpoint](https://ai.google.dev/gemini-api/docs/openai). Google's [pricing page](https://ai.google.dev/gemini-api/docs/pricing) lists free-tier availability; account quotas may vary. Other compatible endpoints work without rewriting the explorer.

| Variable | Purpose | Default |
| --- | --- | --- |
| LLM_BASE_URL | API base path, excluding `/chat/completions` | required |
| LLM_API_KEY | Secret provider key | required |
| LLM_MODEL | Provider model identifier | required |
| LLM_TEMPERATURE | Sampling temperature | 0.3 |
| LLM_TIMEOUT | Per-request timeout in seconds | 30 |
| LLM_MAX_OUTPUT_TOKENS | Output cap per model call | 512; example uses 1024 |
| LLM_REASONING_EFFORT | Optional compatible reasoning setting | unset; example uses minimal |
| LLM_MIN_REQUEST_INTERVAL | Minimum seconds between model requests; 0 disables pacing | 0; example uses 6.5 |
| SANDBOX_API | Owned loopback HTTP endpoint | http://127.0.0.1:8000 |
| AUTO_START_BACKEND | Start missing local backend | 1 |

The explorer defaults to 12 attempted actions, 15 model HTTP calls (including retries/fallbacks), and 120 seconds. Replay has its own 60-second limit. Missing settings, rejected actions, invalid output, provider failures, and backend failures remain visible. No model response is simulated on failure. Provider retries obey the remaining call/time budgets; action POSTs are never automatically retried.

## Tests and measured experiments

```bash
python -m pytest -q
python -u -m agent.evaluation --trials 2 --max-steps 12 --max-llm-calls 15 --timeout 120
python scripts/summarize_evaluations.py
```

Unit tests use labeled scripted model doubles and do **not** establish AI discovery. The evaluation command uses real inference, fresh sessions and a seeded, state-aware random baseline without ordered sequences. It writes individual immutable reports, versioned evaluation JSON/CSV, latest `reports/evaluation.json` and `.csv`, and `docs/RESULTS.md`. Original failed campaigns remain in the versioned files. Model call prompts, latency, usage, errors, and exact action responses are preserved without credentials.

See [measured results](docs/RESULTS.md), [demo script](docs/DEMO.md), [deployment](docs/DEPLOYMENT.md), and the authoritative [API contract](docs/CONTRACT.md).

## Team boundaries and scope

`backend/` and the original backend tests remain owned by the teammate. This implementation works through the public API and does not alter their engine. `agent/evaluation.py` contains a temporary public-schema baseline because no teammate baseline was present; it can be replaced by their measured baseline adapter. No agent module imports the economy implementation, hidden variants, or verifier logic. Operator selection lives outside exploration.

Only the controlled sandbox is supported. This MVP does not integrate with commercial games and does not prove general security or generalization. Cost not measured. The starter and external dependencies are disclosed in the demo document; build-period compliance requires checking the actual hackathon rules.

## Current public demo

[Open the verified temporary demo](https://ringtones-survive-kelkoo-inform.trycloudflare.com). Public-browser checks covered a real AI-selected HTTP action, replay, secure-control regression, and JSON download. Keep the host, Streamlit and tunnel running. This is temporary access, not durable hosting. See `reports/deployment.json` for measured checks. The earlier Flash-Lite model exhausted its daily free quota; failures remain in the results, and the demo now uses the separately verified free Gemini 3.1 Flash-Lite model.
