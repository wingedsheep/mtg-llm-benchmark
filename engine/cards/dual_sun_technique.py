"""
Dual-Sun Technique - Instant
"""

from engine.core.card_system import Card


class DualSunTechnique(Card):
    """Instant (1W)
    Target creature you control gains double strike until end of turn.
    If it has a +1/+1 counter on it, draw a card.
    """

    def __init__(self, **kwargs):
        defaults = {
            "name": "Dual-Sun Technique",
            "mana_cost": "{1}{W}",
            "type_line": "Instant",
            "oracle_text": "Target creature you control gains double strike until end of turn. If it has a +1/+1 counter on it, draw a card.",
            "colors": ["W"],
            "rarity": "uncommon"
        }
        defaults.update(kwargs)
        super().__init__(**defaults)

    def setup_card_behavior(self):
        # Spell effects will be implemented when spell resolution system is added
        pass