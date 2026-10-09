"""Compare downloaded real UI runs with the existing harness's local random baseline.

The deployment is a different host: public spec and observed transitions must match.
This does not evaluate any unpublished local prompt changes or unseen transitions.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.client import SandboxClient
from agent.config import ROOT
from agent.evaluation import random_baseline, summarize
from agent.prompts import public_spec
from agent.replay import replay, attach_replay, secure_control
from agent.report import as_json, now, save_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reports', type=Path, nargs='+')
    parser.add_argument('--seed', type=int, default=2026100901)
    args = parser.parse_args()
    target = ROOT / 'reports' / ('browser_comparison_' + uuid4().hex[:12])
    target.mkdir()
    result = {'generated_at': now(), 'status': 'INCOMPLETE', 'rows': [], 'parity': [],
              'limitation': 'One UI sample per environment; AI ran on the public deployment, '
              'random baseline on local HTTP. Public spec and recorded transitions are checked, '
              'but hidden implementation parity is not proven. Local prompt changes are not evaluated. '
              'No superiority or statistical significance claim.'}
    client = SandboxClient()
    try:
        client.health()
        for index, source in enumerate(args.reports):
            original = json.loads(source.read_text(encoding='utf-8'))
            assert original['discovery_method'] == 'real_llm'
            assert original['llm_calls'] > 0
            assert any(c.get('status') == 'ok' for c in original['model_calls'])
            assert original['public_spec'] == public_spec(client.spec())
            variant = original['operator_variant']
            expected = [f['violation'] for f in original['findings']]
            reproduced = replay(client, original['actions'], variant, expected)
            (target / f'parity_{index}.json').write_text(as_json(reproduced), encoding='utf-8')
            parity = reproduced['complete'] and len(reproduced['actions']) == len(original['actions'])
            for actual, saved in zip(reproduced['actions'], original['actions']):
                parity = parity and all(actual[k] == saved[k] for k in ('action', 'params', 'status', 'before', 'after'))
            if expected:
                parity = parity and reproduced['status'] == 'REPRODUCED'
            else:
                parity = parity and not reproduced['violations']
            result['parity'].append({'source': str(source), 'variant': variant, 'matched': parity})
            assert parity, 'Observed deployment/local transitions differ; comparison stopped.'
            imported = deepcopy(original)
            imported['validation_source'] = str(source)
            imported['validation_note'] = 'Downloaded fresh public-browser run; original prompt, separate host.'
            if imported['findings']:
                secure_control(imported, client)
            imported_path = save_report(imported, target)
            result['rows'].append({**summarize(imported, imported_path, 1), 'max_steps': original['max_steps']})
            client.reset(variant)
            baseline = random_baseline(client, max_steps=original['max_steps'],
                                       timeout_seconds=original['timeout_seconds'], seed=args.seed + index)
            baseline['operator_variant'] = variant
            if baseline['findings']:
                attach_replay(baseline, client, variant)
                secure_control(baseline, client)
            baseline_path = save_report(baseline, target)
            result['rows'].append({**summarize(baseline, baseline_path, 1), 'max_steps': original['max_steps']})
            print(variant, 'AI:', original['status'], 'random:', baseline['status'], flush=True)
        result['status'] = 'COMPLETED'
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        (target / 'comparison.json').write_text(as_json(result), encoding='utf-8')
        print('Comparison evidence:', target, flush=True)


if __name__ == '__main__':
    main()
