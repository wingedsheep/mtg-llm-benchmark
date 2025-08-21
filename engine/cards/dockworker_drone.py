"""
Dockworker Drone - Artifact Creature
"""

from engine.core.card_system import Card
from engine.core.effects_system import EffectFactory, AbilityFactory


class DockworkerDrone(Card):
    """Artifact Creature — Robot (1W) 1/1
    This creature enters with a +1/+1 counter on it.
    When this creature dies, put its counters on target creature you control.
    """

    def __init__(self, **kwargs):
        defaults = {
            "name": "Dockworker Drone",
            "mana_cost": "{1}{W}",
            "type_line": "Artifact Creature — Robot",
            "oracle_text": "This creature enters with a +1/+1 counter on it.\nWhen this creature dies, put its counters on target creature you control.",
            "colors": ["W"],
            "power": "1",
            "toughness": "1",
            "rarity": "common"
        }
        defaults.update(kwargs)
        super().__init__(**defaults)

    def setup_card_behavior(self):
        # ETB effect: enters with +1/+1 counter
        etb_effect = EffectFactory.create_etb_counter_effect("+1/+1", 1)
        self.abilities.append(AbilityFactory.create_etb_ability(etb_effect))

        # Death trigger: move counters to target creature
        death_effect = EffectFactory.create_move_counters_effect()
        self.abilities.append(AbilityFactory.create_death_ability(death_effect))
