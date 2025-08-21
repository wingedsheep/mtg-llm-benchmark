"""
Illvoi Galeblade - Creature
"""

from gameplay.engine.card_system import Card
from gameplay.engine.effects_system import EffectFactory, AbilityFactory


class IllvoiGaleblade(Card):
    """Creature — Jellyfish Warrior (U) 1/1
    Flash
    Flying
    {2}, Sacrifice this creature: Draw a card.
    """

    def __init__(self, **kwargs):
        defaults = {
            "name": "Illvoi Galeblade",
            "mana_cost": "{U}",
            "type_line": "Creature — Jellyfish Warrior",
            "oracle_text": "Flash\nFlying\n{2}, Sacrifice this creature: Draw a card.",
            "colors": ["U"],
            "power": "1",
            "toughness": "1",
            "rarity": "common"
        }
        defaults.update(kwargs)
        super().__init__(**defaults)

    def setup_card_behavior(self):
        # Sacrifice ability: {2}, Sacrifice: Draw a card
        sacrifice_effect = EffectFactory.create_sacrifice_draw_effect()
        self.abilities.append(AbilityFactory.create_sacrifice_ability(sacrifice_effect, "{2}"))
