"""
Banishing Light - Enchantment
"""

from gameplay.engine.card_system import Card
from gameplay.engine.effects_system import Effect, Ability


class BanishingLight(Card):
    """Enchantment (2W)
    When this enchantment enters, exile target nonland permanent an opponent controls
    until this enchantment leaves the battlefield.
    """

    def __init__(self, **kwargs):
        defaults = {
            "name": "Banishing Light",
            "mana_cost": "{2}{W}",
            "type_line": "Enchantment",
            "oracle_text": "When this enchantment enters, exile target nonland permanent an opponent controls until this enchantment leaves the battlefield.",
            "colors": ["W"],
            "rarity": "common"
        }
        defaults.update(kwargs)
        super().__init__(**defaults)

    def setup_card_behavior(self):
        # ETB effect: exile target permanent (simplified for now)
        def exile_effect(game_state, source):
            # TODO: Implement proper targeting system
            # For now, just a placeholder
            pass

        exile_ability = Effect("exile target nonland permanent", exile_effect)
        self.abilities.append(Ability("triggered", "enters_battlefield", effect=exile_ability))
