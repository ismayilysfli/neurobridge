from agent.runner import explore
from agent.replay import replay, attach_replay, secure_control
from agent.client import SandboxError
from conftest import ScriptedLLM, REWARD_SEQUENCE, SHOP_SEQUENCE

def discovered(client, variant='reward_reset', sequence=REWARD_SEQUENCE):
    client.reset(variant)
    return explore(client, llm=ScriptedLLM(sequence))

def test_successful_reproduction_fresh_session(client):
    report = discovered(client)
    old_id = client.session_id
    result = attach_replay(report, client, 'reward_reset')
    assert result['status'] == 'REPRODUCED' and result['complete']
    assert result['session_id'] != old_id
    assert client.session_id == old_id
    assert report['findings'][0]['status'] == 'REPRODUCED'
    assert result['final_state']['coins'] == 200
    assert len(result['actions']) == 3

def test_failed_reproduction_preserves_verification(client):
    report = discovered(client)
    result = attach_replay(report, client, 'secure')
    assert result['status'] == 'FAILED_REPLAY'
    assert report['findings'][0]['status'] == 'FAILED_REPLAY'
    assert report['findings'][0]['verified_by'] == 'backend'
    assert result['actions'][-1]['status'] == 'REJECTED'

def test_same_rule_identifier_required(client):
    report = discovered(client)
    expected = [{'rule_id': 'WRONG_RULE', 'code': 'REPEATED_REWARD'}]
    result = replay(client, report['actions'], 'reward_reset', expected)
    assert result['violations'] and result['status'] == 'FAILED_REPLAY'

def test_secure_control_regression_executes_full_sequence(client):
    report = discovered(client)
    attach_replay(report, client, 'reward_reset')
    result = secure_control(report, client)
    assert result['status'] == 'NO_VIOLATION_OBSERVED'
    assert result['label'] == 'Regression check against secure control'
    assert result['complete'] and len(result['actions']) == 3
    assert result['actions'][-1]['status'] == 'REJECTED'
    assert result['final_state']['coins'] == 150

def test_shop_regression(client):
    report = discovered(client, 'upgrade_resale', SHOP_SEQUENCE)
    assert attach_replay(report, client, 'upgrade_resale')['status'] == 'REPRODUCED'
    result = secure_control(report, client)
    assert result['status'] == 'NO_VIOLATION_OBSERVED'
    assert result['final_state']['coins'] == 80

def test_transport_failure_makes_regression_inconclusive(client, monkeypatch):
    report = discovered(client)
    fresh = client.fresh()
    fresh.action = lambda *args: (_ for _ in ()).throw(SandboxError('ConnectionError'))
    monkeypatch.setattr(client, 'fresh', lambda: fresh)
    result = secure_control(report, client)
    assert result['status'] == 'INCONCLUSIVE' and not result['complete']

def test_replay_cannot_reuse_original_session(client, monkeypatch):
    report = discovered(client)
    fresh = client.fresh()
    monkeypatch.setattr(fresh, 'reset', lambda _: {'session_id': client.session_id, 'state': client.state()})
    monkeypatch.setattr(client, 'fresh', lambda: fresh)
    result = attach_replay(report, client, 'reward_reset')
    assert result['status'] == 'FAILED_REPLAY' and result['actions'] == []

def test_reproduction_requires_complete_sequence(client, monkeypatch):
    report = discovered(client)
    actions = report['actions'] + [{'action': 'claim_reward', 'params': {}}]
    fresh = client.fresh()
    original = fresh.action
    count = [0]
    def fail_last(*args):
        count[0] += 1
        if count[0] == 4:
            raise SandboxError('ConnectionError')
        return original(*args)
    fresh.action = fail_last
    monkeypatch.setattr(client, 'fresh', lambda: fresh)
    result = replay(client, actions, 'reward_reset', [f['violation'] for f in report['findings']])
    assert result['violations'] and result['status'] == 'FAILED_REPLAY' and not result['complete']
