"""
Plains - Basic Land
"""
from gameplay.engine.card_system import Card
from gameplay.engine.effects_system import EffectFactory, AbilityFactory


class Plains(Card):
    """Basic Land — Plains
    {T}: Add {W}.
    """

    def __init__(self, **kwargs):
        defaults = {
            "name": "Plains",
            "mana_cost": "",
            "type_line": "Basic Land — Plains",
            "oracle_text": "{T}: Add {W}.",
            "colors": [],
            "rarity": "basic"
        }
        defaults.update(kwargs)
        super().__init__(**defaults)

    def setup_card_behavior(self):
        # Tap for white mana
        mana_effect = EffectFactory.create_mana_ability('white')
        self.abilities.append(AbilityFactory.create_tap_ability(mana_effect))