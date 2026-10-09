"""Scripted model doubles are software tests, never evidence of AI discovery."""
from copy import deepcopy
import json
from fastapi.testclient import TestClient
import pytest
from backend.app import app
from agent.client import SandboxClient, SandboxError

class ScriptedLLM:
    model = 'mock-model-unit-tests-only'
    is_mock = True
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = 0
        self.records = []
    def complete(self, messages, *, max_attempts, deadline):
        self.calls += 1
        self.records.append({'call': self.calls, 'messages': deepcopy(messages), 'usage': {}, 'latency_seconds': 0})
        output = next(self.outputs)
        if isinstance(output, Exception):
            raise output
        return json.dumps(output) if isinstance(output, dict) else output

class InProcessClient(SandboxClient):
    def __init__(self):
        super().__init__()
        self.http = TestClient(app)
    def _request(self, method, path, payload=None):
        response = self.http.request(method, path, json=payload)
        if not response.is_success:
            raise SandboxError(f'HTTP {response.status_code}: {response.json().get("detail")}', response.status_code)
        return response.json()
    def fresh(self):
        return InProcessClient()

@pytest.fixture
def client():
    value = InProcessClient()
    value.reset('secure')
    return value

def choice(action='claim_reward', params=None):
    return {'action': action, 'params': params or {}, 'reason': 'Unit-test hypothesis, not AI discovery.'}

REWARD_SEQUENCE = [choice(), choice('change_title', {'title': 'UnitTest'}), choice()]
SHOP_SEQUENCE = [choice('buy_item', {'item': 'dagger'}), choice('upgrade_item', {'item': 'dagger'}), choice('sell_item', {'item': 'dagger'})]
