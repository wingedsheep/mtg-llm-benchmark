"""
Updated Dockworker Drone - Artifact Creature
Now uses the prompt system for choosing counter targets.
"""

from engine.core.card_system import Card
from engine.core.common_prompts import CommonPrompts
from engine.core.display_system import game_logger
from engine.core.effects_system import Effect, EffectFactory, AbilityFactory
from engine.core.prompt_system import prompt_manager, PromptError


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

        # Death trigger: move counters to target creature you control
        death_effect = self._create_death_counter_move_effect()
        self.abilities.append(AbilityFactory.create_death_ability(death_effect))

    def _create_death_counter_move_effect(self) -> Effect:
        """Create the death trigger effect that moves counters to another creature"""

        def move_counters_on_death(game_state, source):
            # Get all counters from the dying creature
            counters_to_move = source.counters.copy()

            if not counters_to_move:
                game_logger.log_event(f"{source.name} dies with no counters to move")
                return

            # Find valid targets (creatures controlled by the same player)
            valid_targets = [
                creature for creature in source.controller.get_creatures()
                if creature != source  # Don't target self
            ]

            if not valid_targets:
                game_logger.log_event(f"{source.name} dies but no valid targets for counter movement")
                return

            # Use prompt system to choose target
            target = self._choose_counter_target(game_state, source.controller, valid_targets)

            if target:
                # Move all counters to the target
                total_moved = 0
                for counter_type, amount in counters_to_move.items():
                    target.add_counter(counter_type, amount)
                    total_moved += amount

                game_logger.log_event(
                    f"{source.name} dies, moving {total_moved} counters to {target.name}"
                )
            else:
                game_logger.log_event(f"{source.name} dies but could not choose valid target for counters")

        return Effect("put its counters on target creature you control", move_counters_on_death)

    def _choose_counter_target(self, game_state, controller, valid_targets):
        """Use prompt system to choose which creature should receive the counters"""
        try:
            # Create prompt for choosing target creature
            prompt = CommonPrompts.create_target_prompt(
                title="Choose Counter Target",
                description=f"Choose a creature you control to receive the counters from {self.name}:",
                valid_targets=valid_targets
            )

            # Request choice from controller
            response = prompt_manager.request_prompt(game_state, controller, prompt)

            # Find the selected creature
            selected_id = response.get_single_id()
            if selected_id:
                for creature in valid_targets:
                    if creature.id == selected_id:
                        return creature

            game_logger.log_event(f"Invalid target choice for {self.name}, using default")

        except PromptError as e:
            game_logger.log_event(f"Error in counter target prompt for {self.name}: {e}, using default")

        # Default: use first valid target
        return valid_targets[0] if valid_targets else None

    @classmethod
    def get_card_name(cls) -> str:
        return "Dockworker Drone"
