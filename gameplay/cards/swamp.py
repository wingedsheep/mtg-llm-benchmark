"""
Swamp - Basic Land
"""

from gameplay.engine.card_system import Card
from gameplay.engine.effects_system import EffectFactory, AbilityFactory


class Swamp(Card):
    """Basic Land — Swamp
    {T}: Add {B}.
    """

    def __init__(self, **kwargs):
        defaults = {
            "name": "Swamp",
            "mana_cost": "",
            "type_line": "Basic Land — Swamp",
            "oracle_text": "{T}: Add {B}.",
            "colors": [],
            "rarity": "basic"
        }
        defaults.update(kwargs)
        super().__init__(**defaults)

    def setup_card_behavior(self):
        # Tap for black mana
        mana_effect = EffectFactory.create_mana_ability('black')
        self.abilities.append(AbilityFactory.create_tap_ability(mana_effect))