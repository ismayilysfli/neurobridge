"""Public observation summaries; these checks are not model effectiveness evidence."""
import json
from agent.prompts import messages_for


def test_state_changes_and_coverage_use_only_observed_public_fields():
    spec = {'actions': [{'name': 'inspect'}, {'name': 'exchange'}]}
    before = {'coins': 10, 'welcome_reward_claimed': True, 'variant': 'SECRET'}
    after = {'coins': 10, 'welcome_reward_claimed': False, 'violations': ['SECRET']}
    actions = [{'step': 1, 'action': 'inspect', 'params': {}, 'status': 'ACCEPTED',
                'before': before, 'after': after, 'response': {'new_violations': ['SECRET']}}]
    messages = messages_for(spec, after, actions, {'actions': 2})
    context = json.loads(messages[1]['content'])
    assert context['observations'][0]['changes'] == {
        'welcome_reward_claimed': {'before': True, 'after': False}}
    assert context['untried_actions'] == ['exchange']
    assert 'SECRET' not in json.dumps(messages)
    assert before['variant'] == 'SECRET'  # No mutation of the saved evidence.


def test_rejected_actions_have_no_invented_changes():
    state = {'coins': 10, 'inventory': []}
    actions = [{'step': 1, 'action': 'exchange', 'params': {}, 'status': 'REJECTED',
                'before': state, 'after': state, 'error': 'HTTP 400: Missing inventory'}]
    context = json.loads(messages_for({'actions': [{'name': 'exchange'}]}, state, actions, {})[1]['content'])
    assert context['observations'][0]['changes'] == {}
    assert context['observations'][0]['error'] == 'HTTP 400: Missing inventory'
    assert context['untried_actions'] == []
