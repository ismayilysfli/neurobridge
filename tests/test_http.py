from fastapi.testclient import TestClient
from backend.app import app


def test_full_http_demo():
    client = TestClient(app)
    assert client.get('/api/health').json()['status'] == 'ok'
    spec = client.get('/api/spec').json()
    assert len(spec['actions']) == 5
    create = client.post('/api/sessions', json={'variant':'reward_reset'})
    assert create.status_code == 200
    sid = create.json()['session_id']
    for name, params in [('claim_reward', {}), ('change_title', {'title': 'Hero'}), ('claim_reward', {})]:
        result = client.post(f'/api/sessions/{sid}/actions', json={'action': name, 'params': params})
        assert result.status_code == 200
    state = client.get(f'/api/sessions/{sid}').json()['state']
    assert state['coins'] == 200
    assert len(state['violations']) == 1
