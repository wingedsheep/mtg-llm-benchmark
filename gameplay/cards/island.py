"""
Island - Basic Land
"""

from gameplay.engine.card_system import Card
from gameplay.engine.effects_system import EffectFactory, AbilityFactory


class Island(Card):
    """Basic Land — Island
    {T}: Add {U}.
    """

    def __init__(self, **kwargs):
        defaults = {
            "name": "Island",
            "mana_cost": "",
            "type_line": "Basic Land — Island",
            "oracle_text": "{T}: Add {U}.",
            "colors": [],
            "rarity": "basic"
        }
        defaults.update(kwargs)
        super().__init__(**defaults)

    def setup_card_behavior(self):
        # Tap for blue mana
        mana_effect = EffectFactory.create_mana_ability('blue')
        self.abilities.append(AbilityFactory.create_tap_ability(mana_effect))