"""Single model-guided explorer. The operator configuration never enters this module."""
from copy import deepcopy
import time
from agent.client import SandboxError
from agent.llm import LLMClient, ModelError, ModelBudgetError
from agent.prompts import messages_for, public_spec, observable_state
from agent.schemas import parse_choice, InvalidChoice
from agent.report import new_report, now

def state_delta(before, after):
    coins_before, coins_after = before.get('coins'), after.get('coins')
    return {'coins_before': coins_before, 'coins_after': coins_after,
            'coins_delta': coins_after - coins_before if isinstance(coins_before, (int, float)) and isinstance(coins_after, (int, float)) else None,
            'inventory_before': deepcopy(before.get('inventory', [])),
            'inventory_after': deepcopy(after.get('inventory', [])),
            'inventory_changed': before.get('inventory') != after.get('inventory')}

def explore(client, max_steps=12, max_llm_calls=15, timeout_seconds=120, on_step=None, *, llm=None):
    if max_steps < 0 or max_llm_calls < 0 or timeout_seconds <= 0:
        raise ValueError('Action/call budgets must be nonnegative; timeout must be positive.')
    report = new_report(max_steps, max_llm_calls, timeout_seconds)
    started = time.monotonic()
    deadline = started + timeout_seconds
    original_timeout = getattr(client, 'timeout', None)
    initial_calls = 0
    initial_records = 0
    state = {}
    feedback = None
    try:
        if original_timeout is not None:
            client.timeout = min(original_timeout, max(0.001, deadline - time.monotonic()))
        spec = public_spec(client.spec())
        if time.monotonic() >= deadline:
            report['status'] = 'TIMEOUT'
            return report
        if original_timeout is not None:
            client.timeout = min(original_timeout, max(0.001, deadline - time.monotonic()))
        state = observable_state(client.state())
        report.update(game=spec['game'], public_rules=spec['rules'], public_spec=spec,
                      initial_state=deepcopy(state), session_id=getattr(client, 'session_id', None))
        llm = llm or LLMClient()
        initial_calls, initial_records = llm.calls, len(llm.records)
        report['model'] = llm.model
        report['model_settings'] = {key: getattr(llm, key, None) for key in
                                    ('temperature', 'timeout', 'max_output_tokens', 'min_request_interval', 'reasoning_effort')}
        if getattr(llm, 'is_mock', False):
            report['discovery_method'] = 'mock_llm_unit_test'
        while True:
            used_calls = llm.calls - initial_calls
            report['llm_calls'] = used_calls
            if time.monotonic() >= deadline:
                report['status'] = 'TIMEOUT'
                break
            if len(report['actions']) >= max_steps:
                report['status'] = 'ACTION_BUDGET_EXHAUSTED'
                break
            if used_calls >= max_llm_calls:
                report['status'] = 'MODEL_BUDGET_EXHAUSTED'
                break
            messages = messages_for(spec, state, report['actions'],
                                    {'actions': max_steps - len(report['actions']),
                                     'model_calls': max_llm_calls - used_calls,
                                     'seconds': round(max(0, deadline - time.monotonic()), 2)}, feedback)
            try:
                raw = llm.complete(messages, max_attempts=max_llm_calls - used_calls, deadline=deadline)
            except ModelBudgetError as exc:
                report['errors'].append({'phase': 'model', 'message': str(exc)})
                if exc.reason == 'provider_wait':
                    report['status'] = 'PROVIDER_FAILURE'
                elif exc.reason == 'time' or time.monotonic() >= deadline:
                    report['status'] = 'TIMEOUT'
                else:
                    report['status'] = 'MODEL_BUDGET_EXHAUSTED'
                break
            except ModelError as exc:
                report['errors'].append({'phase': 'model', 'message': str(exc)})
                report['status'] = 'PROVIDER_FAILURE'
                break
            try:
                choice = parse_choice(raw, spec)
            except InvalidChoice as exc:
                feedback = str(exc)
                report['invalid_model_outputs'].append({'call': llm.calls - initial_calls,
                                                         'response': raw, 'error': feedback})
                continue
            feedback = None
            if choice.get('stop'):
                report.update(status='AGENT_STOPPED', stop_reason=choice['reason'])
                break
            if time.monotonic() >= deadline:
                report['status'] = 'TIMEOUT'
                break
            step = {'step': len(report['actions']) + 1, **choice, 'before': deepcopy(state),
                    'status': 'PENDING', 'model_call': llm.calls - initial_calls}
            action_started = time.monotonic()
            abort = False
            try:
                if original_timeout is not None:
                    client.timeout = min(original_timeout, max(0.001, deadline - time.monotonic()))
                response = client.action(choice['action'], choice['params'])
                if not isinstance(response, dict) or not isinstance(response.get('state'), dict) or not isinstance(response.get('new_violations'), list):
                    raise SandboxError('Sandbox action response does not match docs/CONTRACT.md.')
                state = observable_state(response['state'])
                step.update(status='ACCEPTED', response=deepcopy(response), result=response.get('result'))
                for violation in response['new_violations']:
                    report['findings'].append({'status': 'VERIFIED', 'verified_by': 'backend',
                                              'violation': deepcopy(violation), 'hypothesis': choice['reason'],
                                              'discovery_step': step['step'],
                                              'time_to_discovery_seconds': round(time.monotonic() - started, 6)})
            except (SandboxError, ValueError) as exc:
                code = getattr(exc, 'status_code', None)
                step.update(status='REJECTED' if code == 400 else 'ERROR', error=str(exc))
                report['errors'].append({'phase': 'action', 'step': step['step'], 'message': str(exc)})
                # POSTs are never retried: a transport error may have occurred after mutation.
                if code != 400:
                    report['status'] = 'BACKEND_FAILURE'
                    abort = True
            step.update(after=deepcopy(state), latency_seconds=round(time.monotonic() - action_started, 6),
                        **state_delta(step['before'], state))
            report['actions'].append(step)
            report['executed_actions'] = len(report['actions'])
            if on_step:
                try:
                    on_step(deepcopy(step))
                except Exception as exc:
                    report['errors'].append({'phase': 'callback', 'message': type(exc).__name__})
            if report['findings']:
                report['status'] = 'VERIFIED'
                break
            if abort:
                break
    except ModelError as exc:
        report['status'] = 'CONFIGURATION_ERROR'
        report['errors'].append({'phase': 'configuration', 'message': str(exc)})
    except (SandboxError, ValueError, KeyError, TypeError) as exc:
        report['status'] = 'BACKEND_FAILURE'
        report['errors'].append({'phase': 'initialization', 'message': str(exc)})
    finally:
        if original_timeout is not None:
            client.timeout = original_timeout
        report['final_state'] = deepcopy(state)
        if llm is not None:
            report['llm_calls'] = llm.calls - initial_calls
            report['model_calls'] = deepcopy(llm.records[initial_records:])
            for record in report['model_calls']:
                for key, value in record.get('usage', {}).items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        report['usage'][key] = report['usage'].get(key, 0) + value
        report['finished_at'] = now()
        report['duration_seconds'] = round(time.monotonic() - started, 6)
    return report
