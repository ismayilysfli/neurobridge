"""Small, intentionally instrumented game economy for authorized sandbox testing.

BUG VARIANTS ARE PRIVATE TEST FIXTURES. Never pass this module/source to the AI agent.
The public agent interface is only /api/spec, observable state, and action results.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

START_COINS = 100
REWARD_COINS = 50
BUY_PRICE = 40
UPGRADE_PRICE = 10
SELL_PRICE = 20
FIXED_UPGRADED_SELL_PRICE = 30
BUGGY_UPGRADED_SELL_PRICE = 80
VARIANTS = ('secure', 'reward_reset', 'upgrade_resale')

PUBLIC_SPEC = {
    'game': 'Merchant Town (testing sandbox)',
    'starting_coins': START_COINS,
    'rules': [
        {'id': 'R1', 'text': 'The welcome reward can be credited only once per player, regardless of profile changes.'},
        {'id': 'R2', 'text': 'Buying, upgrading and reselling an item must never return more coins than the player spent on that item.'},
    ],
    'actions': [
        {'name': 'claim_reward', 'description': 'Claim the one-time welcome reward (+50 coins).', 'parameters': {}},
        {'name': 'change_title', 'description': 'Change the cosmetic profile title.', 'parameters': {'title': 'string'}},
        {'name': 'buy_item', 'description': 'Buy a dagger for 40 coins.', 'parameters': {'item': 'dagger'}},
        {'name': 'upgrade_item', 'description': 'Upgrade a dagger for 10 coins.', 'parameters': {'item': 'dagger'}},
        {'name': 'sell_item', 'description': 'Sell a dagger back to the shop.', 'parameters': {'item': 'dagger'}},
    ],
    'evaluation_note': 'A finding requires a reproducible action sequence and an observed rule violation.',
}


@dataclass
class Economy:
    variant: str = 'secure'
    coins: int = START_COINS
    title: str = 'Adventurer'
    claimed: bool = False
    reward_credit_count: int = 0
    item: dict[str, Any] | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    violations: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.variant not in VARIANTS:
            raise ValueError('Unknown scenario')

    def observable(self) -> dict[str, Any]:
        return {
            'coins': self.coins,
            'title': self.title,
            'welcome_reward_claimed': self.claimed,
            'inventory': ([{'item': 'dagger', 'upgraded': self.item['upgraded']}] if self.item else []),
            'history': self.history,
            'violations': self.violations,
        }

    def perform(self, name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        if not isinstance(params, dict):
            raise ValueError('params must be an object')
        before = self.coins
        note = ''
        new_violation = None

        if name == 'claim_reward':
            if self.claimed:
                raise ValueError('Welcome reward already claimed')
            self.claimed = True
            self.reward_credit_count += 1
            self.coins += REWARD_COINS
            note = 'Welcome reward credited'
            if self.reward_credit_count > 1:
                new_violation = {'rule_id': 'R1', 'code': 'REPEATED_REWARD', 'evidence': f'Welcome reward credited {self.reward_credit_count} times'}
        elif name == 'change_title':
            title = params.get('title')
            if not isinstance(title, str) or not (1 <= len(title) <= 32):
                raise ValueError('title must be a string of length 1..32')
            self.title = title
            if self.variant == 'reward_reset':
                self.claimed = False  # intentionally injected defect in the simulator
            note = 'Cosmetic title changed'
        elif name == 'buy_item':
            self._require_dagger(params)
            if self.item is not None:
                raise ValueError('Only one dagger can be held at a time')
            if self.coins < BUY_PRICE:
                raise ValueError('Insufficient coins')
            self.coins -= BUY_PRICE
            self.item = {'upgraded': False, 'total_spent': BUY_PRICE}
            note = 'Dagger purchased'
        elif name == 'upgrade_item':
            self._require_dagger(params)
            if self.item is None:
                raise ValueError('No dagger to upgrade')
            if self.item['upgraded']:
                raise ValueError('Dagger is already upgraded')
            if self.coins < UPGRADE_PRICE:
                raise ValueError('Insufficient coins')
            self.coins -= UPGRADE_PRICE
            self.item['upgraded'] = True
            self.item['total_spent'] += UPGRADE_PRICE
            note = 'Dagger upgraded'
        elif name == 'sell_item':
            self._require_dagger(params)
            if self.item is None:
                raise ValueError('No dagger to sell')
            upgraded = self.item['upgraded']
            spent = self.item['total_spent']
            payout = (BUGGY_UPGRADED_SELL_PRICE if self.variant == 'upgrade_resale' else FIXED_UPGRADED_SELL_PRICE) if upgraded else SELL_PRICE
            self.coins += payout
            self.item = None
            note = f'Dagger sold for {payout} coins (spent {spent} coins on this item)'
            if payout > spent:
                new_violation = {'rule_id': 'R2', 'code': 'PROFITABLE_ITEM_CYCLE', 'evidence': f'Payout {payout} > spent {spent} coins'}
        else:
            raise ValueError(f'Unknown action: {name}')

        record = {'step': len(self.history) + 1, 'action': name, 'params': params, 'coins_before': before, 'coins_after': self.coins, 'note': note}
        self.history.append(record)
        if new_violation is not None:
            new_violation['step'] = record['step']
            self.violations.append(new_violation)
        return {'result': note, 'state': self.observable(), 'new_violations': [new_violation] if new_violation else []}

    @staticmethod
    def _require_dagger(params: dict[str, Any]) -> None:
        if params.get('item') != 'dagger':
            raise ValueError('item must be dagger')
