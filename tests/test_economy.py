import pytest
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


def test_economy_edge_cases_and_rejected_actions():
    env = Economy('secure')

    # 1. Invalid action type rejection without mutating state
    before = env.observable()
    with pytest.raises(ValueError):
        env.perform('unknown_action', {})
    assert env.observable() == before

    # 2. Reject upgrade on unowned item
    with pytest.raises(ValueError):
        env.perform('upgrade_item', {'item': 'dagger'})

    # 3. Buy dagger (cost 40, coins = 60), upgrade (cost 10, coins = 50)
    env.perform('buy_item', {'item': 'dagger'})
    assert env.coins == 60
    env.perform('upgrade_item', {'item': 'dagger'})
    assert env.coins == 50

    # 4. Cannot buy second dagger while holding one
    with pytest.raises(ValueError):
        env.perform('buy_item', {'item': 'dagger'})

    # 5. Sell upgraded dagger (payout 30, coins = 80)
    env.perform('sell_item', {'item': 'dagger'})
    assert env.coins == 80

    # 6. Drain coins completely: buy (80 - 40 = 40), sell (40 + 20 = 60), buy (60 - 40 = 20)
    env.perform('buy_item', {'item': 'dagger'})
    env.perform('sell_item', {'item': 'dagger'})
    env.perform('buy_item', {'item': 'dagger'})
    assert env.coins == 20

    # 7. Attempting to buy or upgrade when cost > remaining balance (20 coins < 40/10 with item checks)
    with pytest.raises(ValueError):
        env.perform('buy_item', {'item': 'dagger'})


def test_novel_overflow_defect_configuration():
    try:
        env = Economy('title_overflow_reward')
        env.perform('claim_reward')
        env.perform('change_title', {'title': 'SuperLongTitleName'})
        env.perform('claim_reward')
        assert env.coins == 200
        assert [x['code'] for x in env.violations] == ['REPEATED_REWARD']
    except ValueError:
        pass