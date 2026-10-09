import json
import time
from unittest.mock import Mock
import requests
import pytest
from agent.llm import LLMClient, ModelError
from agent.runner import explore
from agent.schemas import parse_choice, InvalidChoice, parameter_schema
from agent.prompts import messages_for
from agent.report import save_report
from agent.client import SandboxClient
from conftest import ScriptedLLM, choice, REWARD_SEQUENCE

def test_valid_json_and_fenced_json(client):
    raw = json.dumps(choice())
    assert parse_choice(raw, client.spec())['action'] == 'claim_reward'
    assert parse_choice('```json\n' + raw + '\n```', client.spec())['params'] == {}

@pytest.mark.parametrize('raw', ['not json', '[]', '{', '{}', '{"stop":true}'])
def test_malformed_model_json(client, raw):
    with pytest.raises(InvalidChoice):
        parse_choice(raw, client.spec())

def test_unknown_action(client):
    with pytest.raises(InvalidChoice, match='Unknown action'):
        parse_choice(choice('imaginary'), client.spec())

@pytest.mark.parametrize('value', [choice('buy_item', {'item': 'sword'}), choice('buy_item'),
                                  choice('change_title', {'title': 7}), choice('claim_reward', {'extra': True})])
def test_invalid_parameters(client, value):
    with pytest.raises(InvalidChoice, match='parameters'):
        parse_choice(value, client.spec())

def test_standard_json_schema():
    spec = {'actions': [{'name': 'buy', 'parameters': {'type': 'object', 'properties': {'count': {'type': 'integer', 'minimum': 1, 'maximum': 3}}, 'required': ['count']}}]}
    assert parse_choice(choice('buy', {'count': 2}), spec)
    with pytest.raises(InvalidChoice):
        parse_choice(choice('buy', {'count': True}), spec)
    assert parameter_schema({'item': ['dagger', 'axe']})['properties']['item']['enum'] == ['dagger', 'axe']

def test_action_budget_and_rejection_count(client):
    llm = ScriptedLLM([choice(), choice(), choice()])
    steps = []
    report = explore(client, max_steps=2, llm=llm, on_step=steps.append)
    assert report['status'] == 'ACTION_BUDGET_EXHAUSTED'
    assert report['executed_actions'] == 2 and llm.calls == 2
    assert [a['status'] for a in report['actions']] == ['ACCEPTED', 'REJECTED']
    assert len(steps) == 2 and report['final_state']['coins'] == 150

def test_call_budget_and_invalid_outputs(client):
    llm = ScriptedLLM(['broken'] * 3)
    report = explore(client, max_llm_calls=3, llm=llm)
    assert report['status'] == 'MODEL_BUDGET_EXHAUSTED'
    assert report['llm_calls'] == 3 and report['executed_actions'] == 0
    assert len(report['invalid_model_outputs']) == 3

def test_observation_updates_and_transcript(client):
    llm = ScriptedLLM([choice(), choice('change_title', {'title': 'Observer'})])
    report = explore(client, max_steps=2, llm=llm)
    second = json.loads(llm.records[1]['messages'][1]['content'])
    assert second['state']['coins'] == 150
    assert second['observations'][0]['after']['welcome_reward_claimed'] is True
    assert report['actions'][0]['coins_delta'] == 50
    assert report['actions'][1]['before']['coins'] == 150
    assert report['actions'][1]['after']['title'] == 'Observer'
    assert report['actions'][0]['response']['state']['coins'] == 150

def test_private_data_never_enters_prompt(client):
    spec = client.spec()
    spec.update(variant='SECRET_VARIANT', hidden_bug='SECRET_BUG')
    state = client.state()
    state.update(variant='SECRET_VARIANT', violations=[{'code': 'SECRET_VERIFIER'}], history=[{'note': 'SECRET_LEDGER'}], spent_ledger='SECRET_SPENT')
    raw = json.dumps(messages_for(spec, state, [], {}))
    assert 'SECRET_' not in raw
    assert 'new_violations' not in raw

def test_backend_verification_only(client):
    client.reset('reward_reset')
    llm = ScriptedLLM(REWARD_SEQUENCE + [choice()])
    report = explore(client, llm=llm)
    assert report['status'] == 'VERIFIED' and report['executed_actions'] == 3
    assert report['findings'][0]['verified_by'] == 'backend'
    assert report['findings'][0]['violation']['code'] == 'REPEATED_REWARD'
    assert llm.calls == 3

def test_hypothesis_is_not_verification(client):
    action = choice()
    action['reason'] = 'I found a vulnerability.'
    report = explore(client, max_steps=1, llm=ScriptedLLM([action]))
    assert report['findings'] == []

def test_model_failure_preserves_partial_trace(client):
    report = explore(client, llm=ScriptedLLM([choice(), ModelError('Provider unavailable')]))
    assert report['status'] == 'PROVIDER_FAILURE'
    assert len(report['actions']) == 1 and report['errors']

def response(status=200, content=None, text='', headers=None):
    value = Mock()
    value.status_code = status
    value.ok = 200 <= status < 300
    value.text = text
    value.headers = headers or {}
    value.json.return_value = content or {'choices': [{'message': {'content': json.dumps(choice())}}], 'usage': {'total_tokens': 10}}
    return value

def model(**kwargs):
    return LLMClient(base_url='https://provider.invalid/v1', api_key='unit-test-key', model='test', min_request_interval=0, **kwargs)

def test_provider_timeout_is_visible_and_bounded(client, monkeypatch):
    post = Mock(side_effect=requests.Timeout())
    monkeypatch.setattr('agent.llm.requests.post', post)
    llm = model(max_retries=1)
    report = explore(client, max_llm_calls=5, llm=llm)
    assert report['status'] == 'PROVIDER_FAILURE'
    assert report['llm_calls'] == 2 and post.call_count == 2
    assert 'Timeout' in report['errors'][0]['message']
    assert all(r['latency_seconds'] >= 0 for r in report['model_calls'])

def test_json_mode_fallback_consumes_calls(client, monkeypatch):
    post = Mock(side_effect=[response(400, text='response_format is not supported'), response()])
    monkeypatch.setattr('agent.llm.requests.post', post)
    llm = model()
    report = explore(client, max_steps=1, max_llm_calls=2, llm=llm)
    assert report['llm_calls'] == 2 and report['executed_actions'] == 1
    assert 'response_format' in post.call_args_list[0].kwargs['json']
    assert 'response_format' not in post.call_args_list[1].kwargs['json']
    assert report['usage']['total_tokens'] == 10

def test_transient_retry_cannot_exceed_call_budget(client, monkeypatch):
    post = Mock(return_value=response(429))
    monkeypatch.setattr('agent.llm.requests.post', post)
    monkeypatch.setattr('agent.llm.time.sleep', lambda _: None)
    report = explore(client, max_llm_calls=2, llm=model())
    assert report['llm_calls'] == 2 and report['executed_actions'] == 0
    assert report['status'] == 'MODEL_BUDGET_EXHAUSTED'

def test_provider_auth_failure_no_fake_action(client, monkeypatch):
    monkeypatch.setattr('agent.llm.requests.post', Mock(return_value=response(401)))
    report = explore(client, llm=model())
    assert report['status'] == 'PROVIDER_FAILURE' and not report['actions']
    assert 'unit-test-key' not in json.dumps(report)

def test_wall_clock_limit_prevents_action(client):
    llm = ScriptedLLM([choice()])
    real_complete = llm.complete
    def delayed(*args, **kwargs):
        time.sleep(0.02)
        return real_complete(*args, **kwargs)
    llm.complete = delayed
    report = explore(client, timeout_seconds=0.015, llm=llm)
    assert report['status'] == 'TIMEOUT' and not report['actions']

def test_zero_budgets(client):
    llm = ScriptedLLM([])
    report = explore(client, max_steps=0, llm=llm)
    assert report['executed_actions'] == 0 and llm.calls == 0

def test_expired_session(client):
    client.session_id = 'missing-session'
    report = explore(client, llm=ScriptedLLM([]))
    assert report['status'] == 'BACKEND_FAILURE' and not report['actions']

def test_reports_are_unique_and_json(client, tmp_path):
    report = explore(client, max_steps=1, llm=ScriptedLLM([choice()]))
    one, two = save_report(report, tmp_path), save_report(report, tmp_path)
    assert one != two
    assert json.loads(one.read_text())['executed_actions'] == 1

def test_external_sandbox_rejected():
    with pytest.raises(ValueError, match='loopback'):
        SandboxClient('https://third-party.invalid')

def test_callback_cannot_modify_transcript(client):
    def callback(step):
        step['params']['extra'] = 'mutated'
    report = explore(client, max_steps=1, llm=ScriptedLLM([choice()]), on_step=callback)
    assert report['actions'][0]['params'] == {}

def test_gemini_array_error_and_daily_quota_are_visible(client, monkeypatch):
    error = [{'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED',
                       'message': 'Daily quota exhausted. unit-test-key',
                       'details': [{'retryDelay': '38142s'}]}}]
    post = Mock(return_value=response(429, content=error))
    monkeypatch.setattr('agent.llm.requests.post', post)
    report = explore(client, max_llm_calls=15, llm=model())
    assert report['status'] == 'PROVIDER_FAILURE'
    assert report['llm_calls'] == 1 and not report['actions']
    assert report['model_calls'][0]['provider_error']['status'] == 'RESOURCE_EXHAUSTED'
    assert 'unit-test-key' not in json.dumps(report)

def test_missing_model_settings_are_configuration_error(client, monkeypatch):
    monkeypatch.setattr('agent.llm.load_environment', lambda: None)
    for key in ('LLM_BASE_URL', 'LLM_API_KEY', 'LLM_MODEL'):
        monkeypatch.delenv(key, raising=False)
    report = explore(client)
    assert report['status'] == 'CONFIGURATION_ERROR'
    assert report['llm_calls'] == 0 and report['executed_actions'] == 0
    assert 'LLM_API_KEY' in report['errors'][0]['message']

def test_variant_and_verifier_never_enter_live_context(client):
    client.reset('reward_reset')
    llm = ScriptedLLM(REWARD_SEQUENCE)
    explore(client, llm=llm)
    prompts = json.dumps([record['messages'] for record in llm.records])
    assert 'reward_reset' not in prompts and 'upgrade_resale' not in prompts
    assert 'REPEATED_REWARD' not in prompts and 'new_violations' not in prompts
