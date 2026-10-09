"""Repeatable real-model experiments and a seeded public-schema random baseline.
No backend internals or fixture solutions are imported. Every run gets a fresh session.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
import csv
import json
import random
import re
import time
from uuid import uuid4
from agent.client import SandboxClient, SandboxError
from agent.config import ROOT, load_environment
from agent.llm import LLMClient
from agent.prompts import public_spec, observable_state
from agent.report import new_report, save_report, as_json, now
from agent.runner import explore, state_delta
from agent.replay import attach_replay, secure_control
from agent.schemas import parameter_schema

VARIANTS = ('reward_reset', 'upgrade_resale', 'secure')

def sample_value(schema, rng):
    if 'const' in schema:
        return schema['const']
    if 'enum' in schema:
        return rng.choice(schema['enum'])
    if 'default' in schema:
        return deepcopy(schema['default'])
    kind = schema.get('type', 'string')
    if kind == 'string':
        return 'Tester' + str(rng.randrange(10000))
    if kind == 'integer':
        return rng.randint(int(schema.get('minimum', 0)), int(schema.get('maximum', schema.get('minimum', 0) + 10)))
    if kind == 'number':
        return rng.uniform(schema.get('minimum', 0), schema.get('maximum', 10))
    if kind == 'boolean':
        return bool(rng.randrange(2))
    if kind == 'array':
        return [sample_value(schema.get('items', {}), rng) for _ in range(schema.get('minItems', 0))]
    if kind == 'object':
        return {key: sample_value(value, rng) for key, value in schema.get('properties', {}).items()}
    return None

def eligible_actions(spec, state):
    """Apply only observable preconditions; no ordered sequences or verifier feedback.
    Both agents may read reward eligibility, inventory and public price descriptions.
    Action-specific filters are the current game's adapter, not a hidden answer key.
    """
    choices = []
    for action in spec['actions']:
        name = action['name']
        if name == 'claim_reward' and state.get('welcome_reward_claimed'):
            continue
        if name in ('sell_item', 'upgrade_item') and not state.get('inventory'):
            continue
        price = re.search(r'(?:for|costs?)\s+(\d+)\s+coins', action.get('description', ''), re.I)
        if price and name in ('buy_item', 'upgrade_item') and state.get('coins', 0) < int(price.group(1)):
            continue
        choices.append(action)
    return choices

def random_baseline(client, *, max_steps=12, timeout_seconds=120, seed=0):
    rng = random.Random(seed)
    report = new_report(max_steps, 0, timeout_seconds)
    report.update(model=None, discovery_method='seeded_state_aware_random', seed=seed)
    started = time.monotonic()
    state = {}
    original_timeout = client.timeout
    try:
        spec = public_spec(client.spec())
        state = observable_state(client.state())
        report.update(game=spec['game'], public_rules=spec['rules'], public_spec=spec,
                      initial_state=deepcopy(state), session_id=client.session_id)
        for index in range(max_steps):
            if time.monotonic() - started >= timeout_seconds:
                report['status'] = 'TIMEOUT'
                break
            candidates = eligible_actions(spec, state)
            if not candidates:
                report['status'] = 'NO_ELIGIBLE_ACTIONS'
                break
            selected = rng.choice(candidates)
            schema = parameter_schema(selected.get('parameters', {}))
            params = {key: sample_value(value, rng) for key, value in schema.get('properties', {}).items()}
            step = {'step': index + 1, 'action': selected['name'], 'params': params,
                    'reason': 'Uniform random choice among actions with observable eligibility.', 'before': deepcopy(state)}
            tick = time.monotonic()
            try:
                client.timeout = min(original_timeout, max(0.001, timeout_seconds - (time.monotonic() - started)))
                response = client.action(step['action'], params)
                state = observable_state(response['state'])
                step.update(status='ACCEPTED', response=deepcopy(response))
                for violation in response['new_violations']:
                    report['findings'].append({'status': 'VERIFIED', 'verified_by': 'backend',
                                              'violation': deepcopy(violation), 'hypothesis': step['reason'],
                                              'discovery_step': index + 1,
                                              'time_to_discovery_seconds': round(time.monotonic() - started, 6)})
            except SandboxError as exc:
                step.update(status='REJECTED' if exc.status_code == 400 else 'ERROR', error=str(exc))
                report['errors'].append({'phase': 'action', 'step': index + 1, 'message': str(exc)})
                if exc.status_code != 400:
                    report['status'] = 'BACKEND_FAILURE'
            step.update(after=deepcopy(state), latency_seconds=round(time.monotonic() - tick, 6), **state_delta(step['before'], state))
            report['actions'].append(step)
            if report['findings']:
                report['status'] = 'VERIFIED'
                break
            if report['status'] == 'BACKEND_FAILURE':
                break
        else:
            report['status'] = 'ACTION_BUDGET_EXHAUSTED'
    except (SandboxError, ValueError, KeyError) as exc:
        report['status'] = 'BACKEND_FAILURE'
        report['errors'].append({'phase': 'baseline', 'message': str(exc)})
    finally:
        client.timeout = original_timeout
        report.update(final_state=deepcopy(state), executed_actions=len(report['actions']),
                      finished_at=now(), duration_seconds=round(time.monotonic() - started, 6))
    return report

def summarize(report, path, trial):
    return {'run_id': report['run_id'], 'trial': trial, 'method': report['discovery_method'],
            'variant': report['operator_variant'], 'model': report['model'],
            'verified': bool(report['findings']),
            'reproduced': report['replay'].get('status') == 'REPRODUCED',
            'actions': report['executed_actions'], 'llm_calls': report['llm_calls'],
            'time_to_discovery_seconds': report['findings'][0]['time_to_discovery_seconds'] if report['findings'] else None,
            'duration_seconds': report['duration_seconds'],
            'replay_seconds': report['replay'].get('duration_seconds', 0),
            'invalid_actions': sum(a['status'] == 'REJECTED' for a in report['actions']),
            'invalid_model_outputs': len(report['invalid_model_outputs']),
            'model_errors': sum(c.get('status') == 'error' for c in report['model_calls']),
            'secure_control_status': report['secure_control'].get('status'),
            'verified_flags_on_secure': len(report['findings']) if report['operator_variant'] == 'secure' else 0,
            'status': report['status'], 'seed': report.get('seed'), 'report': path.name}

def write_results(rows, evaluation_id, args):
    report = {'evaluation_id': evaluation_id, 'generated_at': now(), 'trials_per_environment_per_method': args.trials,
              'max_steps': args.max_steps, 'max_llm_calls': args.max_llm_calls, 'timeout_seconds': args.timeout,
              'environments': list(VARIANTS), 'model': LLMClient().model,
              'baseline': 'Uniform random among publicly eligible actions; seeded parameters from public schemas; no action sequences.',
              'limitation': 'Small controlled sample; no statistical significance or generalization claim. Failed runs are retained.',
              'rows': rows}
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    # Versioned outputs preserve prior evaluations; stable names are latest summaries only.
    payload = as_json(report)
    (reports / f'evaluation_{evaluation_id}.json').write_text(payload)
    (reports / 'evaluation.json').write_text(payload)
    for name in (f'evaluation_{evaluation_id}.csv', 'evaluation.csv'):
        if rows:
            with (reports / name).open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    lines = ['# Measured evaluation results', '', f'Generated: {report["generated_at"]}. Evaluation `{evaluation_id}`.', '',
             f'Model: `{report["model"]}`. Budgets per discovery run: {args.max_steps} actions (including rejected actions), '
             f'{args.max_llm_calls} model HTTP calls, {args.timeout}s. Each experiment creates an independent session.', '',
             'The AI receives public rules, schemas and observable state only. Configuration names and verifier evidence never enter model prompts.', '',
             'Baseline: uniform random among actions with observable eligibility. Parameters use public schemas. Seeds are saved. '
             'No ordered exploit sequences are used; the baseline is state aware rather than intentionally weakened.', '',
             '| Method | Environment | Completed trials | Verified | Reproduced | Mean actions | Model errors |',
             '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for method in ('real_llm', 'seeded_state_aware_random'):
        for variant in VARIANTS:
            group = [r for r in rows if r['method'] == method and r['variant'] == variant]
            if group:
                lines.append(f'| {method} | {variant} | {len(group)} | {sum(r["verified"] for r in group)} | {sum(r["reproduced"] for r in group)} | {sum(r["actions"] for r in group)/len(group):.1f} | {sum(r["model_errors"] for r in group)} |')
    lines += ['', '## Failures and limits', '',
              'Every failed or exhausted run remains in the JSON/CSV and individual reports. A negative finding means no verified violation was discovered within that budget, not that the game is secure. '
              'A backend-verified flag on the secure scenario is reported for investigation; it is not automatically called a false positive. '
              'A failed replay stays labeled FAILED_REPLAY.', '',
              'Only two deliberately defective toy economies and their secure control are available. Sample size is small; no statistical superiority or real-game generalization is established. '
              'Unit tests use scripted model doubles and are excluded from these AI results. Replay and regression do not count as additional discoveries. Cost not measured.', '',
              'Recorded failures:', '']
    failures = [r for r in rows if not r['verified'] or r['status'] == 'FAILED_REPLAY']
    lines += [f'- `{r["method"]}` / `{r["variant"]}` / trial {r["trial"]}: `{r["status"]}`; {r["actions"]} actions, {r["llm_calls"]} calls, {r["model_errors"]} model errors.' for r in failures] or ['None among the completed runs.']
    (ROOT / 'docs' / 'RESULTS.md').write_text('\n'.join(lines) + '\n')

def main():
    load_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials', type=int, default=2)
    parser.add_argument('--max-steps', type=int, default=12)
    parser.add_argument('--max-llm-calls', type=int, default=15)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--seed', type=int, default=20261009)
    args = parser.parse_args()
    if args.trials < 1:
        parser.error('--trials must be positive')
    evaluation_id = uuid4().hex[:12]
    rows = []
    model = LLMClient()
    client = SandboxClient()
    client.health()
    for trial in range(1, args.trials + 1):
        for variant in VARIANTS:
            for method in ('real_llm', 'seeded_state_aware_random'):
                print(f'RUN {trial} {variant} {method}', flush=True)
                client.reset(variant)
                if method == 'real_llm':
                    def progress(step):
                        print(f'  {step["step"]}: {step["action"]} {step["status"]} {step["coins_before"]}->{step["coins_after"]}', flush=True)
                    result = explore(client, args.max_steps, args.max_llm_calls, args.timeout, progress, llm=model)
                else:
                    result = random_baseline(client, max_steps=args.max_steps, timeout_seconds=args.timeout,
                                             seed=args.seed + trial * 100 + VARIANTS.index(variant))
                result.update(operator_variant=variant, evaluation_id=evaluation_id, trial=trial)
                if result['findings']:
                    attach_replay(result, client, variant)
                    secure_control(result, client)
                path = save_report(result)
                rows.append(summarize(result, path, trial))
                write_results(rows, evaluation_id, args)
                print(f'  RESULT {result["status"]}; {result["executed_actions"]} actions; {result["llm_calls"]} calls; saved {path.name}', flush=True)
    print('Evaluation saved:', evaluation_id, flush=True)

if __name__ == '__main__':
    main()
