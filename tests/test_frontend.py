"""UI software checks use a scripted model, not autonomous AI evidence."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
from agent.client import SandboxError
from conftest import InProcessClient, ScriptedLLM, REWARD_SEQUENCE

APP = Path(__file__).resolve().parents[1] / 'frontend' / 'app.py'

def setup_app(monkeypatch, tmp_path):
    (tmp_path / 'reports').mkdir()
    monkeypatch.setattr('agent.config.ROOT', tmp_path)
    monkeypatch.setattr('agent.report.ROOT', tmp_path)
    monkeypatch.setattr('agent.client.SandboxClient', lambda *args, **kwargs: InProcessClient())
    monkeypatch.setattr('frontend.local_backend.ensure_backend', lambda *args, **kwargs: {'status': 'ok'})
    for key, value in [('LLM_BASE_URL', 'https://test.invalid/v1'), ('LLM_API_KEY', 'mock-key'), ('LLM_MODEL', 'mock-model-unit-tests-only')]:
        monkeypatch.setenv(key, value)
    return AppTest.from_file(str(APP), default_timeout=15)

def button(app, label):
    return next(x for x in app.button if x.label == label)

def test_dashboard_ignores_non_report_json(monkeypatch, tmp_path):
    app = setup_app(monkeypatch, tmp_path)
    (tmp_path / 'reports' / 'integrity.json').write_text('[]')
    (tmp_path / 'reports' / 'broken.json').write_text('{')
    app.run()
    assert not app.exception
    assert not button(app, 'START AI SECURITY TEST').disabled

def test_dashboard_run_replay_control_and_download(monkeypatch, tmp_path):
    app = setup_app(monkeypatch, tmp_path)
    monkeypatch.setattr('agent.llm.LLMClient', lambda **kwargs: ScriptedLLM(REWARD_SEQUENCE))
    app.run()
    button(app, 'START AI SECURITY TEST').click().run()
    assert not app.exception
    report = app.session_state['report']
    assert report['status'] == 'REPRODUCED'
    assert report['discovery_method'] == 'mock_llm_unit_test'
    button(app, 'REPLAY FINDING').click().run()
    assert app.session_state['report']['replay']['status'] == 'REPRODUCED'
    button(app, 'RUN AGAINST SECURE CONTROL').click().run()
    assert app.session_state['report']['secure_control']['status'] == 'NO_VIOLATION_OBSERVED'
    assert not app.exception
    downloads = app.get('download_button')
    assert downloads


def test_dashboard_backend_failure_disables_start(monkeypatch, tmp_path):
    app = setup_app(monkeypatch, tmp_path)
    def fail(*args, **kwargs):
        raise RuntimeError('Backend unavailable')
    monkeypatch.setattr('frontend.local_backend.ensure_backend', fail)
    app.run()
    assert not app.exception
    assert button(app, 'START AI SECURITY TEST').disabled
    assert any('Backend unavailable' in x.value for x in app.error)
