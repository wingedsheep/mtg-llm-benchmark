"""
Effects and abilities system for the MTG engine.
Handles triggered abilities, activated abilities, static effects, and spell effects.
"""

from typing import Callable, Any, TYPE_CHECKING

from gameplay.engine.core_types import GameEvent, Zone

if TYPE_CHECKING:
    from game_state import GameState
    from gameplay.engine.card_system import Card

class Effect:
    """Base class for card effects"""

    def __init__(self, description: str, effect_func: Callable):
        self.description = description
        self.effect_func = effect_func

    def execute(self, game_state: 'GameState', source: 'Card', **kwargs) -> Any:
        """Execute this effect"""
        return self.effect_func(game_state, source, **kwargs)

class Ability:
    """Represents card abilities (triggered, activated, static)"""

    def __init__(self, ability_type: str, trigger_condition: str = None,
                 cost: str = None, effect: Effect = None):
        self.ability_type = ability_type  # "triggered", "activated", "static"
        self.trigger_condition = trigger_condition
        self.cost = cost
        self.effect = effect
        self.is_usable = True

    def can_activate(self, source: 'Card') -> bool:
        """Check if this ability can be activated"""
        if self.ability_type != "activated":
            return False

        if not self.is_usable:
            return False

        # Check tap cost
        if self.cost == "T" and source.is_tapped:
            return False

        # Add more cost checking logic here as needed
        return True

    def activate(self, game_state: 'GameState', source: 'Card'):
        """Activate this ability"""
        if not self.can_activate(source):
            return False

        # Pay costs
        if self.cost == "T":
            source.is_tapped = True

        # Execute effect
        if self.effect:
            self.effect.execute(game_state, source)

        return True

class TriggerManager:
    """Manages triggered abilities and their conditions"""

    def __init__(self):
        self.pending_triggers = []

    def check_triggers(self, event: GameEvent, game_state: 'GameState'):
        """Check all permanents for triggered abilities that match this event"""
        for player in game_state.players:
            for card in player.battlefield:
                self._check_card_triggers(card, event, game_state)

    def _check_card_triggers(self, card: 'Card', event: GameEvent, game_state: 'GameState'):
        """Check if a specific card has triggers for this event"""
        for ability in card.abilities:
            if hasattr(ability, 'ability_type') and ability.ability_type == "triggered":
                if self._trigger_matches_event(ability, event, card):
                    self.pending_triggers.append((ability, card))

    def _trigger_matches_event(self, ability: Ability, event: GameEvent, source: 'Card') -> bool:
        """Check if a triggered ability matches the given event"""
        if not ability.trigger_condition:
            return False

        # Simple trigger matching - can be expanded
        if ability.trigger_condition == "enters_battlefield":
            return (event.event_type == "enters_battlefield" and
                    event.data.get("card") == source)

        if ability.trigger_condition == "dies":
            return (event.event_type == "dies" and
                    event.data.get("card") == source)

        # Add more trigger conditions as needed
        return False

    def resolve_triggers(self, game_state: 'GameState'):
        """Resolve all pending triggers"""
        while self.pending_triggers:
            ability, source = self.pending_triggers.pop(0)
            if ability.effect:
                ability.effect.execute(game_state, source)

# Common effect factories for easy card creation
class EffectFactory:
    """Factory for creating common card effects"""

    @staticmethod
    def create_etb_counter_effect(counter_type: str, amount: int = 1) -> Effect:
        """Create an effect that adds counters when entering battlefield"""

        def add_counters(game_state, source):
            source.add_counter(counter_type, amount)

        return Effect(f"enters with {amount} {counter_type} counter{'s' if amount != 1 else ''}",
                      add_counters)

    @staticmethod
    def create_mana_ability(color: str) -> Effect:
        """Create a mana-producing ability"""

        def add_mana(game_state, source):
            source.controller.mana_pool.add_mana(color, 1)

        color_symbol = {
            'white': '{W}',
            'blue': '{U}',
            'black': '{B}',
            'red': '{R}',
            'green': '{G}',
            'colorless': '{C}'
        }.get(color, f'{{{color}}}')

        return Effect(f"Add {color_symbol}", add_mana)

    @staticmethod
    def create_sacrifice_draw_effect() -> Effect:
        """Create an effect that sacrifices the source to draw a card"""

        def sacrifice_draw(game_state, source):
            if source in source.controller.battlefield:
                # Move to graveyard
                source.controller.battlefield.remove(source)
                source.controller.graveyard.append(source)
                source.zone = Zone.GRAVEYARD

                # Draw card
                source.controller.draw_card()

                # Trigger death event
                death_event = GameEvent("dies", card=source)
                game_state.trigger_manager.check_triggers(death_event, game_state)

        return Effect("Draw a card", sacrifice_draw)

    @staticmethod
    def create_move_counters_effect() -> Effect:
        """Create an effect that moves counters to another creature"""

        def move_counters(game_state, source):
            # Simplified: for now just remove counters
            # TODO: Implement proper targeting
            source.counters.clear()

        return Effect("put its counters on target creature you control", move_counters)

# Ability factory for common ability patterns
class AbilityFactory:
    """Factory for creating common abilities"""

    @staticmethod
    def create_etb_ability(effect: Effect) -> Ability:
        """Create an enters-the-battlefield triggered ability"""
        return Ability("triggered", "enters_battlefield", effect=effect)

    @staticmethod
    def create_death_ability(effect: Effect) -> Ability:
        """Create a death triggered ability"""
        return Ability("triggered", "dies", effect=effect)

    @staticmethod
    def create_tap_ability(effect: Effect) -> Ability:
        """Create a tap activated ability"""
        return Ability("activated", cost="T", effect=effect)

    @staticmethod
    def create_sacrifice_ability(effect: Effect, additional_cost: str = None) -> Ability:
        """Create a sacrifice activated ability"""
        cost = additional_cost if additional_cost else ""
        return Ability("activated", cost=cost, effect=effect)
