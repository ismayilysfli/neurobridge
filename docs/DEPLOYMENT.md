# Deployment

## Verified local deployment

Streamlit serves the dashboard and starts a separate FastAPI process when missing. The sandbox binds only to loopback. `frontend/local_backend.py` checks health, uses a Linux file lock, and keeps the child process across Streamlit reruns. Logs live in `reports/backend.log`; sessions are in memory and disappear on backend restart. Local subprocess operation was exercised on this machine; remote hosting remains a separate verification step.

## Free temporary public demo

Run Streamlit locally, then expose only its UI:

```bash
python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
cloudflared tunnel --url http://127.0.0.1:8501 --protocol http2 --no-autoupdate
```

Use the HTTPS URL printed by cloudflared. Keep Streamlit, its sandbox, the tunnel and the host running during judging. The sandbox port must not be tunneled. A Cloudflare [Quick Tunnel](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) is temporary, has no uptime guarantee, and changes URL when restarted. This is a demo deployment, not durable hosting. The public app uses the server's configured provider quota.

Check in a fresh browser: rendered rules, connected status, real AI run, timeline, replay, secure-control responses, and JSON download. Check the WebSocket connection as well as the HTML response. See `reports/deployment.json` for actually measured verification rather than assuming a tunnel works.

Current verified temporary URL: https://ringtones-survive-kelkoo-inform.trycloudflare.com. The public browser test executed a real model-selected action, loaded a labeled recorded finding, executed fresh-session replay/control requests, and downloaded valid JSON.

## Durable Streamlit hosting

1. Put the source, requirements, `.streamlit/config.toml`, and reports you intend to share in a GitHub repository. Exclude `.env`, `.venv`, logs, cache and `.streamlit/secrets.toml`.
2. Select `frontend/app.py` as the entrypoint and Python 3.12 on the chosen Streamlit host.
3. Configure `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` and optional budgets in secrets. Set `SANDBOX_API="http://127.0.0.1:8000"`.
4. Confirm the host permits local subprocesses and loopback listeners; the helper needs both. Check health and actual replay after cold startup.
5. Verify a fresh-browser visit from another machine before submitting the URL.

Streamlit documents [dependency files](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies) and [secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management). No remote Streamlit account or durable deployment has been verified here. If the chosen host disallows local subprocesses, use the tested local app plus a demo tunnel, or choose a host that supports this process model. Do not expose the sandbox API publicly.
