from backend.economy import Economy


def run(econ, actions):
    for action, params in actions:
        econ.perform(action, params)
    return econ


def test_reward_reset_discovery_ground_truth():
    actions = [('claim_reward', {}), ('change_title', {'title': 'Mage'}), ('claim_reward', {})]
    vuln = run(Economy('reward_reset'), actions)
    assert vuln.coins == 200
    assert [x['code'] for x in vuln.violations] == ['REPEATED_REWARD']


def test_secure_reward_is_not_repeatable():
    env = Economy('secure')
    env.perform('claim_reward')
    env.perform('change_title', {'title': 'Mage'})
    try:
        env.perform('claim_reward')
    except ValueError as exc:
        assert 'already claimed' in str(exc)
    else:
        raise AssertionError('secure reward must reject a second claim')
    assert not env.violations


def test_upgrade_resale_profit_detected():
    actions = [('buy_item', {'item': 'dagger'}), ('upgrade_item', {'item': 'dagger'}), ('sell_item', {'item': 'dagger'})]
    vuln = run(Economy('upgrade_resale'), actions)
    assert vuln.coins == 130
    assert [x['code'] for x in vuln.violations] == ['PROFITABLE_ITEM_CYCLE']


def test_secure_upgrade_resale_is_not_profitable():
    actions = [('buy_item', {'item': 'dagger'}), ('upgrade_item', {'item': 'dagger'}), ('sell_item', {'item': 'dagger'})]
    secure = run(Economy('secure'), actions)
    assert secure.coins == 80
    assert not secure.violations


def test_invalid_actions_do_not_mutate_state():
    env = Economy('secure')
    before = env.observable()
    try:
        env.perform('sell_item', {'item': 'dagger'})
    except ValueError:
        pass
    else:
        raise AssertionError('sell without item should error')
    assert env.observable() == before
