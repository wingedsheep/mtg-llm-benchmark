"""
Mountain - Basic Land
"""

from engine.core.card_system import Card
from engine.core.effects_system import EffectFactory, AbilityFactory


class Mountain(Card):
    """Basic Land — Mountain
    {T}: Add {R}.
    """

    def __init__(self, **kwargs):
        defaults = {
            "name": "Mountain",
            "mana_cost": "",
            "type_line": "Basic Land — Mountain",
            "oracle_text": "{T}: Add {R}.",
            "colors": [],
            "rarity": "basic"
        }
        defaults.update(kwargs)
        super().__init__(**defaults)

    def setup_card_behavior(self):
        # Tap for red mana
        mana_effect = EffectFactory.create_mana_ability('red')
        self.abilities.append(AbilityFactory.create_tap_ability(mana_effect))