"""Streamlit entry point: real discovery, backend verification, replay and export."""
from pathlib import Path
import os
import sys
import json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
from agent.config import load_environment, ROOT
from agent.client import SandboxClient, SandboxError
from agent.llm import LLMClient, ModelError
from agent.runner import explore
from agent.prompts import public_spec, observable_state
from agent.replay import attach_replay, secure_control
from agent.report import save_report, as_json
from frontend.local_backend import ensure_backend

st.set_page_config(page_title='Game Economy Exploit Tester', page_icon='🛡️', layout='wide')
load_environment()
try:
    secrets = dict(st.secrets)
except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
    secrets = {}
def setting(name, default=''):
    return secrets.get(name, os.getenv(name, default))

st.title('Game Economy Exploit Tester')
st.caption('Autonomous AI Testing for Game Economy Vulnerabilities')
base = setting('SANDBOX_API', 'http://127.0.0.1:8000')
configured = all(setting(k) for k in ('LLM_BASE_URL', 'LLM_API_KEY', 'LLM_MODEL'))
backend_ok = False
backend_error = ''
try:
    ensure_backend(base)
    client = SandboxClient(base)
    spec = public_spec(client.spec())
    backend_ok = True
except (SandboxError, RuntimeError, ValueError, OSError) as exc:
    backend_error = str(exc)
    spec = {}
cols = st.columns(3)
cols[0].metric('Sandbox', 'Connected' if backend_ok else 'Disconnected')
cols[1].metric('LLM configuration', 'Configured' if configured else 'Unconfigured')
cols[2].metric('Model', setting('LLM_MODEL', 'Unconfigured'))
if backend_error:
    st.error(backend_error)
if not configured:
    st.info('Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL in .env or Streamlit secrets to enable real AI testing.')

SCENARIOS = {'Reward scenario': 'reward_reset', 'Trading scenario': 'upgrade_resale', 'Secure control': 'secure'}
with st.sidebar:
    st.header('Test configuration')
    scenario = st.selectbox('Controlled environment', list(SCENARIOS))
    variant = SCENARIOS[scenario]
    st.caption('Owned test economies. Scenario identity is excluded from model context.')
    max_steps = st.number_input('Maximum actions', min_value=1, max_value=30, value=12)
    max_calls = st.number_input('Maximum model calls', min_value=1, max_value=40, value=15)
    timeout = st.number_input('Exploration timeout (seconds)', min_value=10, max_value=300, value=120, step=10)
    temperature = st.slider('Temperature', 0.0, 1.0, float(setting('LLM_TEMPERATURE', '0.3')), 0.1)
    if st.button('Reset session', disabled=not backend_ok, use_container_width=True):
        try:
            created = client.reset(variant)
            st.session_state.game_session = {'variant': variant, 'id': created['session_id']}
            st.session_state.pop('report', None)
            st.session_state.pop('loaded_record', None)
            st.rerun()
        except SandboxError as exc:
            st.error(str(exc))

if backend_ok:
    st.subheader(spec['game'])
    with st.expander('Public rules and action schemas', expanded=True):
        left, right = st.columns(2)
        with left:
            for rule in spec['rules']:
                st.markdown(f"**{rule['id']}** · {rule['text']}")
        with right:
            for action in spec['actions']:
                st.markdown(f"**`{action['name']}`** · {action['description']}")
                st.code(as_json(action['parameters']), language='json')
    session = st.session_state.get('game_session')
    if not session or session['variant'] != variant:
        try:
            created = client.reset(variant)
            session = {'variant': variant, 'id': created['session_id']}
            st.session_state.game_session = session
        except SandboxError as exc:
            st.error(str(exc))
    if session:
        client.session_id = session['id']
        try:
            state = observable_state(client.state())
            a, b, c = st.columns(3)
            a.metric('Starting coins', spec['starting_coins'])
            current_currency = b.empty()
            current_currency.metric('Current coins', state.get('coins', '—'))
            current_inventory = c.empty()
            current_inventory.metric('Inventory items', len(state.get('inventory', [])))
            if state.get('inventory'):
                st.json(state['inventory'])
        except SandboxError as exc:
            st.error(str(exc))

start = st.button('START AI SECURITY TEST', type='primary', disabled=not (backend_ok and configured), use_container_width=True)
live = st.empty()

def render_timeline(actions, target):
    with target.container():
        st.subheader('Action timeline')
        if not actions:
            st.caption('Waiting for a real model-selected action…')
        for step in actions:
            with st.expander(f"STEP {step['step']:02d} · {step['action']} · {step['status']} · {step.get('coins_before', '—')} → {step.get('coins_after', '—')} coins", expanded=True):
                st.write(step['reason'])
                st.json(step['params'])
                st.caption(f"Execution: {step.get('latency_seconds', 0):.3f}s · Inventory changed: {step.get('inventory_changed', False)}")
                if step.get('error'):
                    st.warning(step['error'])
                elif step.get('result'):
                    st.write(step['result'])
                if step.get('inventory_changed'):
                    st.json({'before': step['inventory_before'], 'after': step['inventory_after']})

if start:
    try:
        model = LLMClient(base_url=setting('LLM_BASE_URL'), api_key=setting('LLM_API_KEY'),
                          model=setting('LLM_MODEL'), temperature=temperature,
                          timeout=float(setting('LLM_TIMEOUT', '30')),
                          max_output_tokens=int(setting('LLM_MAX_OUTPUT_TOKENS', '512')))
        created = client.reset(variant)
        st.session_state.game_session = {'variant': variant, 'id': created['session_id']}
        steps = []
        def on_step(step):
            steps.append(step)
            render_timeline(steps, live)
            if 'current_currency' in globals():
                current_currency.metric('Current coins', step['after'].get('coins', '—'))
                current_inventory.metric('Inventory items', len(step['after'].get('inventory', [])))
        with st.spinner('Model-guided exploration is executing real sandbox actions…'):
            report = explore(client, int(max_steps), int(max_calls), int(timeout), on_step, llm=model)
        report['operator_variant'] = variant
        report['scenario_label'] = scenario
        st.session_state.report = report
        st.session_state.pop('loaded_record', None)
        if report['findings']:
            with st.spinner('Replaying the exact sequence in a fresh session…'):
                attach_replay(report, client, variant)
        st.session_state.report_path = str(save_report(report))
    except (ModelError, SandboxError, ValueError) as exc:
        st.error(str(exc))

report = st.session_state.get('report')
if report:
    if st.session_state.get('loaded_record'):
        st.info('Recorded real-model run · captured ' + report['started_at'] + '. This is saved evidence, not a new live discovery.')
    render_timeline(report['actions'], live)
    st.caption(f"Run {report['run_id']} · {report.get('scenario_label', '')} · {report['model']} · {report['status']}")
    metrics = st.columns(4)
    metrics[0].metric('Actions attempted', report['executed_actions'])
    metrics[1].metric('Model HTTP calls', report['llm_calls'])
    metrics[2].metric('Runtime', f"{report['duration_seconds']:.2f}s")
    metrics[3].metric('Verified findings', len(report['findings']))
    if report['errors'] or report['invalid_model_outputs']:
        with st.expander('Errors and rejected model outputs', expanded=True):
            st.json({'errors': report['errors'], 'invalid_model_outputs': report['invalid_model_outputs']})
    if report['actions']:
        st.subheader('Wallet changes')
        import pandas as pd
        wallet = [{'step': 0, 'coins': report['initial_state'].get('coins')}]
        wallet += [{'step': a['step'], 'coins': a.get('coins_after')} for a in report['actions']]
        st.line_chart(pd.DataFrame(wallet).set_index('step'))
    st.subheader('Verified findings')
    if report['findings']:
        for finding in report['findings']:
            violation = finding['violation']
            text = f"{finding['status']} · {violation.get('rule_id', violation.get('rule', 'Unknown rule'))} · {violation.get('code', 'Economic rule violation')}"
            if finding['status'] == 'REPRODUCED':
                st.success(text)
            else:
                st.warning(text)
            st.write('Model hypothesis: ' + finding['hypothesis'])
            st.json(violation)
        with st.expander('Initial and final economic states'):
            st.json({'initial': report['initial_state'], 'final': report['final_state']})
        left, right = st.columns(2)
        if left.button('REPLAY FINDING', disabled=not backend_ok, use_container_width=True):
            with st.spinner('Executing recorded actions in a new session…'):
                attach_replay(report, client, report['operator_variant'])
                st.session_state.report_path = str(save_report(report))
            st.rerun()
        reproduced = all(f['status'] == 'REPRODUCED' for f in report['findings'])
        if right.button('RUN AGAINST SECURE CONTROL', disabled=not (backend_ok and reproduced), use_container_width=True):
            with st.spinner('Running regression check against secure control…'):
                secure_control(report, client)
                st.session_state.report_path = str(save_report(report))
            st.rerun()
        if report['replay']:
            st.write('Replay outcome: ' + report['replay']['status'])
            with st.expander('Replay evidence'):
                st.json(report['replay'])
        if report['secure_control']:
            st.write('Regression check against secure control: ' + report['secure_control']['status'])
            st.caption('This checks only the recorded sequence; it does not establish that the whole game is secure.')
            with st.expander('Secure-control responses'):
                st.json(report['secure_control'])
    else:
        st.info('No verified vulnerability discovered within the test budget.')
    st.download_button('DOWNLOAD JSON REPORT', data=as_json(report),
                       file_name=f"economy-{report['run_id']}.json", mime='application/json', use_container_width=True, on_click='ignore')
    with st.expander('Model usage and full report'):
        st.json(report)
else:
    st.info('Select a controlled environment and start an AI security test. Findings require backend verification and fresh-session replay.')

with st.expander('Recorded real-model evidence'):
    saved = {}
    for path in sorted((ROOT / 'reports').glob('*.json'), key=lambda p: p.stat().st_mtime):
        try:
            record = json.loads(path.read_text())
            if isinstance(record, dict) and record.get('discovery_method') == 'real_llm' and record.get('llm_calls', 0) > 0:
                saved[record['run_id']] = record
        except (ValueError, OSError, KeyError):
            continue
    if saved:
        ordered = sorted(saved, key=lambda run_id: saved[run_id]['started_at'], reverse=True)
        def record_label(run_id):
            record = saved[run_id]
            return f"{record['started_at']} · {record.get('operator_variant', 'sandbox')} · {record['status']} · {run_id[:8]}"
        selected_record = st.selectbox('Previously executed model runs', ordered,
                                      format_func=record_label, key='saved_run_id')
        if st.button('LOAD RECORDED RUN'):
            st.session_state.report = saved[selected_record]
            st.session_state.loaded_record = True
            st.rerun()
    else:
        st.caption('No recorded real-model runs available yet.')

evaluation_path = ROOT / 'reports' / 'evaluation.json'
if evaluation_path.exists():
    with st.expander('Measured AI and random-baseline evaluation'):
        try:
            measured = json.loads(evaluation_path.read_text())
            st.caption(f"Evaluation {measured['evaluation_id']} · {measured['max_steps']} actions per run · {measured['max_llm_calls']} model calls · {measured['timeout_seconds']} seconds")
            st.dataframe(measured['rows'], hide_index=True, use_container_width=True)
            st.write(measured['limitation'])
            st.download_button('DOWNLOAD EVALUATION JSON', data=as_json(measured), file_name='evaluation.json', mime='application/json', on_click='ignore')
        except (ValueError, OSError, KeyError) as exc:
            st.error('Could not read the measured evaluation: ' + str(exc))
st.caption('AI-guided adversarial testing for game economies · Cost not measured · No third-party game integrations')
