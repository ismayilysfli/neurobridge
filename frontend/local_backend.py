"""Start at most one local sandbox process; keep its API on loopback."""
from __future__ import annotations
import atexit
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse
import requests
from agent.config import ROOT

_MUTEX = threading.Lock()
_OWNED = []

def healthy(base_url):
    try:
        response = requests.get(base_url + '/api/health', timeout=1, allow_redirects=False)
        return response.status_code == 200 and response.json().get('status') == 'ok'
    except (requests.RequestException, ValueError):
        return False

def _shutdown():
    for process in _OWNED:
        if process.poll() is None:
            process.terminate()
atexit.register(_shutdown)

def ensure_backend(base_url='http://127.0.0.1:8000', startup_timeout=15):
    parsed = urlparse(base_url)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise RuntimeError('The sandbox must run on loopback.')
    if healthy(base_url):
        return {'status': 'ok', 'started': False}
    if os.getenv('AUTO_START_BACKEND', '1').lower() not in ('1', 'true', 'yes'):
        raise RuntimeError('Backend unavailable; start uvicorn on loopback or enable AUTO_START_BACKEND.')
    if parsed.path not in ('', '/'):
        raise RuntimeError('Automatic backend startup requires a loopback URL without a path.')
    with _MUTEX:
        reports = ROOT / 'reports'
        reports.mkdir(exist_ok=True)
        with (reports / '.backend.lock').open('a') as lock_file:
            # Linux hosts: also coordinate different Streamlit worker processes.
            try:
                import fcntl
                fcntl.flock(lock_file, fcntl.LOCK_EX)
            except ImportError:
                pass
            if healthy(base_url):
                return {'status': 'ok', 'started': False}
            env = dict(os.environ)
            env.pop('LLM_API_KEY', None)
            with (reports / 'backend.log').open('a') as log:
                process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app:app',
                           '--host', parsed.hostname, '--port', str(parsed.port or 8000)],
                           cwd=ROOT, env=env, stdout=log, stderr=log)
            _OWNED.append(process)
            end = time.monotonic() + startup_timeout
            while time.monotonic() < end:
                if healthy(base_url):
                    return {'status': 'ok', 'started': True}
                if process.poll() is not None:
                    raise RuntimeError('Backend startup failed. Inspect reports/backend.log.')
                time.sleep(0.2)
            process.terminate()
            raise RuntimeError('Backend did not become healthy before the startup timeout.')
