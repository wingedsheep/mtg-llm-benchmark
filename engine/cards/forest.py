"""
Forest - Basic Land
"""

from engine.core.card_system import Card
from engine.core.effects_system import EffectFactory, AbilityFactory


class Forest(Card):
    """Basic Land — Forest
    {T}: Add {G}.
    """

    def __init__(self, **kwargs):
        defaults = {
            "name": "Forest",
            "mana_cost": "",
            "type_line": "Basic Land — Forest",
            "oracle_text": "{T}: Add {G}.",
            "colors": [],
            "rarity": "basic"
        }
        defaults.update(kwargs)
        super().__init__(**defaults)

    def setup_card_behavior(self):
        # Tap for green mana
        mana_effect = EffectFactory.create_mana_ability('green')
        self.abilities.append(AbilityFactory.create_tap_ability(mana_effect))