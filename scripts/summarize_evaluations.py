"""Combine measured campaigns without dropping failures or mixing their budgets."""
import csv
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent.config import ROOT
from agent.report import now, as_json

reports=ROOT/'reports'
campaigns=[]
for path in reports.glob('evaluation_*.json'):
    try:
        value=json.loads(path.read_text())
        if isinstance(value,dict) and 'rows' in value and 'evaluation_id' in value and 'campaigns' not in value:
            campaigns.append(value)
    except (ValueError,OSError):
        continue
campaigns.sort(key=lambda x:x['generated_at'])
rows=[]
for campaign in campaigns:
    for row in campaign['rows']:
        rows.append({**row,'campaign':campaign['evaluation_id'],'max_steps':campaign['max_steps'],
                     'max_llm_calls':campaign['max_llm_calls'],'timeout_seconds':campaign['timeout_seconds']})
combined={'evaluation_id':'all-measured-campaigns','generated_at':now(),
          'max_steps':'varies by campaign','max_llm_calls':'varies by campaign','timeout_seconds':'varies by campaign',
          'models':sorted({c['model'] for c in campaigns}),
          'campaigns':[{k:c[k] for k in ('evaluation_id','generated_at','model','trials_per_environment_per_method','max_steps','max_llm_calls','timeout_seconds')} for c in campaigns],
          'rows':rows,
          'limitation':'Small toy sample, different campaign budgets, repeated baseline seeds across the first two campaigns, and provider quota failures. No statistical superiority or generalization claim.'}
(reports/'evaluation.json').write_text(as_json(combined))
(reports/'evaluation_campaigns.json').write_text(as_json(combined))
if rows:
    with (reports/'evaluation.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
lines=['# Measured evaluation results','',f'Generated: {combined["generated_at"]}. All completed campaigns, including failures, are listed below.','',
       'Environments: Merchant Town owned sandbox; `reward_reset`, `upgrade_resale`, and `secure`. All runs create fresh sessions. '
       'Scenario labels, backend source and verifier evidence are withheld from the model. The model receives only public rules/schemas and actual observations.','',
       'Random baseline: uniform random among actions with observable reward eligibility, inventory and affordability; schema-valid seeded parameters; no ordered sequences. '
       'Rejected API actions count toward the same game-action budget as the AI. Baseline code is a temporary public-API evaluation adapter because no teammate baseline was present.','']
for campaign in campaigns:
    lines += [f'## Campaign {campaign["evaluation_id"]}','',
              f'Model: `{campaign["model"]}`. Trials per environment per method: {campaign["trials_per_environment_per_method"]}. '
              f'Budget: {campaign["max_steps"]} game actions, {campaign["max_llm_calls"]} model HTTP calls, {campaign["timeout_seconds"]} seconds. '
              'Retries and invalid outputs consume the model budget. Replay/regression do not count as additional discoveries.','',
              '| Method | Environment | Trials | Verified | Reproduced | Mean actions | Mean runtime (s) | Provider errors |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for method in ('real_llm','seeded_state_aware_random'):
        for variant in ('reward_reset','upgrade_resale','secure'):
            group=[r for r in campaign['rows'] if r['method']==method and r['variant']==variant]
            if group:
                lines.append(f'| {method} | {variant} | {len(group)} | {sum(r["verified"] for r in group)} | {sum(r["reproduced"] for r in group)} | {sum(r["actions"] for r in group)/len(group):.1f} | {sum(r["duration_seconds"] for r in group)/len(group):.2f} | {sum(r["model_errors"] for r in group)} |')
    lines += ['', 'Failures/exhausted runs:', '']
    failures=[r for r in campaign['rows'] if not r['verified'] or not r['reproduced']]
    lines += [f'- `{r["method"]}` / `{r["variant"]}` / trial {r["trial"]}: `{r["status"]}`, {r["actions"]} actions, {r["llm_calls"]} model calls, {r["invalid_actions"]} rejected actions, {r["invalid_model_outputs"]} invalid model outputs.' for r in failures] or ['None.']
lines += ['', '## Interpretation and limitations','',
          'The benchmark question is whether AI-guided exploration beats a simple unguided tester under the same action budget. '
          'These measurements do not establish that it does: the random baseline also finds defects, the sample is very small, and quota interruptions make several AI runs incomplete. '
          'Compare methods within a campaign, not across different budgets/models. Repeated baseline seeds in the first two campaigns are replication checks, not additional independent samples.','',
          'Flash-Lite reached this account\'s daily free-tier limit. A diagnostic 429 response reported 20 requests per model per day and a retry delay longer than the entire exploration budget. '
          'Those incomplete runs stay recorded. Request pacing cannot recover exhausted daily quota. Gemini 2.5 Flash was independently probed and executed a real action; later experiments record its exact identity.','',
          'No model hypothesis is a confirmed finding without backend verification. Secure-scenario verified flags are visible in JSON/CSV and must be investigated; a failure or negative result never proves the game secure. '
          'A regression check establishes only that the recorded sequence did not trigger a verifier rule in that secure session. '
          'No confirmed false finding was manufactured; nonreproducing findings would remain FAILED_REPLAY. Unit/UI tests use labeled mocked models and are excluded from these measurements.','',
          'Only two deliberately defective toy configurations and one secure control are available. No independent held-out backend scenario was supplied. '
          'No commercial-game integration, statistical significance, cost/savings estimate, or generalization claim is supported. Cost not measured.','',
          'The single-action connectivity probe, initial standalone reward discovery, and public-browser single-action test are saved separately. They are not silently included in the matched benchmark denominators. '
          'Individual reports include exact actions/responses, model prompts, measured latency and provider token usage. Original versioned campaign JSON/CSV are retained.']
(ROOT/'docs'/'RESULTS.md').write_text('\n'.join(lines)+'\n')
print('Aggregated',len(campaigns),'campaigns and',len(rows),'measured runs.')
