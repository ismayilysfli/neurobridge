"""Deterministic replay/reporting layer; never invokes the discovery model."""
from copy import deepcopy
import time
from agent.client import SandboxError
from agent.prompts import observable_state
from agent.runner import state_delta

def violation_identity(violation):
    # Same public rule identifier is mandatory; code disambiguates when supplied.
    rule = violation.get('rule_id') or violation.get('rule') or violation.get('id')
    if not rule:
        return None
    return (rule, violation.get('code'))

def replay(client, actions, variant, expected_violations, *, timeout_seconds=60, original_session_id=None):
    started = time.monotonic()
    deadline = started + timeout_seconds
    result = {'status': 'RUNNING', 'variant': variant, 'session_id': None,
              'actions': [], 'violations': [], 'errors': [], 'complete': False,
              'matched_violations': [], 'expected_violations': deepcopy(expected_violations)}
    fresh = client.fresh()
    original_timeout = getattr(fresh, 'timeout', None)
    state = {}
    try:
        if original_timeout is not None:
            fresh.timeout = min(original_timeout, max(0.001, deadline - time.monotonic()))
        created = fresh.reset(variant)
        result['session_id'] = created['session_id']
        if created['session_id'] == (original_session_id or getattr(client, 'session_id', None)):
            raise SandboxError('Replay did not create a fresh session.')
        state = observable_state(created['state'])
        result['initial_state'] = deepcopy(state)
        for index, action in enumerate(actions, 1):
            if time.monotonic() >= deadline:
                raise SandboxError('Replay wall-clock timeout.')
            before = deepcopy(state)
            step = {'step': index, 'action': action['action'], 'params': deepcopy(action['params']), 'before': before}
            tick = time.monotonic()
            try:
                if original_timeout is not None:
                    fresh.timeout = min(original_timeout, max(0.001, deadline - time.monotonic()))
                response = fresh.action(step['action'], step['params'])
                if not isinstance(response.get('state'), dict) or not isinstance(response.get('new_violations'), list):
                    raise SandboxError('Replay response does not match the API contract.')
                state = observable_state(response['state'])
                step.update(status='ACCEPTED', response=deepcopy(response))
                result['violations'].extend(deepcopy(response['new_violations']))
            except (SandboxError, ValueError) as exc:
                step.update(status='REJECTED' if getattr(exc, 'status_code', None) == 400 else 'ERROR', error=str(exc))
                result['errors'].append({'step': index, 'message': str(exc)})
                if getattr(exc, 'status_code', None) != 400:
                    step.update(after=deepcopy(state), latency_seconds=round(time.monotonic() - tick, 6), **state_delta(before, state))
                    result['actions'].append(step)
                    raise
            step.update(after=deepcopy(state), latency_seconds=round(time.monotonic() - tick, 6), **state_delta(before, state))
            result['actions'].append(step)
        result['complete'] = time.monotonic() <= deadline
        actual = {violation_identity(v) for v in result['violations'] if violation_identity(v)}
        expected = [violation_identity(v) for v in expected_violations]
        result['matched_violations'] = [list(v) for v in expected if v and v in actual]
        result['status'] = 'REPRODUCED' if result['complete'] and expected and all(v and v in actual for v in expected) else 'FAILED_REPLAY'
    except (SandboxError, ValueError, KeyError, TypeError) as exc:
        result['status'] = 'FAILED_REPLAY'
        result['errors'].append({'phase': 'replay', 'message': str(exc)})
    result['final_state'] = deepcopy(state)
    result['duration_seconds'] = round(time.monotonic() - started, 6)
    return result

def attach_replay(report, client, variant):
    result = replay(client, report['actions'], variant, [f['violation'] for f in report['findings']],
                    original_session_id=report.get('session_id'))
    report['replay'] = result
    for finding in report['findings']:
        identity = violation_identity(finding['violation'])
        finding['status'] = 'REPRODUCED' if result['complete'] and identity and list(identity) in result['matched_violations'] else 'FAILED_REPLAY'
    if report['findings']:
        report['status'] = result['status']
    return result

def secure_control(report, client):
    result = replay(client, report['actions'], 'secure', [f['violation'] for f in report['findings']],
                    original_session_id=report.get('session_id'))
    result['label'] = 'Regression check against secure control'
    if not result['complete']:
        result['status'] = 'INCONCLUSIVE'
    elif result['violations']:
        result['status'] = 'VIOLATION_OBSERVED'
    else:
        result['status'] = 'NO_VIOLATION_OBSERVED'
    report['secure_control'] = result
    return result
