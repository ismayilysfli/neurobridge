"""Immutable JSON snapshots with unique names and measured metadata."""
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from agent.config import ROOT

def now():
    return datetime.now(timezone.utc).isoformat()
def new_report(max_steps, max_llm_calls, timeout_seconds):
    return {'run_id': str(uuid4()), 'model': None, 'environment': 'owned loopback sandbox',
            'started_at': now(), 'finished_at': None, 'max_steps': max_steps,
            'max_llm_calls': max_llm_calls, 'timeout_seconds': timeout_seconds,
            'llm_calls': 0, 'executed_actions': 0, 'duration_seconds': 0,
            'status': 'RUNNING', 'actions': [], 'findings': [], 'model_calls': [],
            'invalid_model_outputs': [], 'replay': {}, 'secure_control': {}, 'errors': [],
            'usage': {}, 'cost': 'Cost not measured', 'discovery_method': 'real_llm'}
def as_json(report):
    return json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)
def save_report(report, directory=None):
    target = Path(directory) if directory else ROOT / 'reports'
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{report['run_id']}_{uuid4().hex[:8]}.json"
    with path.open('x', encoding='utf-8') as output:
        output.write(as_json(report))
    return path
