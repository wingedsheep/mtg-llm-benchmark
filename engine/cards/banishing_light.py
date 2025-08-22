"""
Updated Banishing Light implementation with integrated targeting system.
Now uses the prompt system for target selection.
"""

from typing import List, Optional, TYPE_CHECKING

from engine.core.card_system import Card, exile_tracker
from engine.core.core_types import GameEvent, Zone
from engine.core.display_system import game_logger
from engine.core.targeting_system import targeting_system, TargetingError

if TYPE_CHECKING:
    from engine.core.targeting_system import TargetFilter
    from engine.core.game_state import GameState
    from engine.core.player_system import Player


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

    def get_target_filter(self) -> Optional['TargetFilter']:
        """This spell targets nonland permanents opponents control"""
        return targeting_system.create_nonland_permanent_opponent_filter()

    def requires_targets(self) -> bool:
        """Banishing Light requires a target"""
        return True

    def resolve_spell(self, game_state: 'GameState', caster: 'Player', targets: List['Card'] = None) -> bool:
        """
        Resolve Banishing Light - request target if needed, then exile and enter battlefield

        Note: In the current system, targets should be provided by the spell system.
        If no targets are provided, this method will request them.
        """
        try:
            # If no targets provided, request them using targeting system
            if not targets:
                try:
                    target_filter = self.get_target_filter()
                    targets = [targeting_system.request_single_target(game_state, caster, target_filter, self.name)]
                except TargetingError as e:
                    game_logger.log_event(f"{self.name} cannot resolve: {e}")
                    # Put in graveyard if no valid targets
                    caster.graveyard.append(self)
                    self.zone = Zone.GRAVEYARD
                    return False

            # Banishing Light enters the battlefield first
            caster.battlefield.append(self)
            self.zone = Zone.BATTLEFIELD
            self.controller = caster

            game_logger.log_event(f"{self.name} enters the battlefield")

            # Then trigger its ETB ability
            if targets and len(targets) > 0:
                target = targets[0]  # Should be exactly one target

                # Exile the target
                exile_tracker.exile_card(self, target)
                game_logger.log_event(f"{self.name} exiles {target.name}")

                # Trigger death event if creature died
                if target.is_creature():
                    death_event = GameEvent("dies", card=target)
                    game_state.trigger_manager.check_triggers(death_event, game_state)
            else:
                game_logger.log_event(f"{self.name} enters but has no valid targets")

            # Trigger ETB event for this enchantment
            etb_event = GameEvent("enters_battlefield", card=self)
            game_state.trigger_manager.check_triggers(etb_event, game_state)

            return True

        except Exception as e:
            game_logger.log_event(f"Error resolving {self.name}: {e}")
            # Put in graveyard if resolution failed
            caster.graveyard.append(self)
            self.zone = Zone.GRAVEYARD
            return False

    def leaves_battlefield(self):
        """When Banishing Light leaves, return exiled cards"""
        super().leaves_battlefield()

        # Return all cards this Banishing Light exiled
        returned_cards = exile_tracker.return_exiled_cards(self)

        if returned_cards:
            returned_names = [card.name for card in returned_cards]
            game_logger.log_event(f"{self.name} returns: {', '.join(returned_names)}")

    def setup_card_behavior(self):
        """Banishing Light's behavior is handled in resolve_spell"""
        # No abilities to set up - this is a spell with a resolution effect
        pass

    @classmethod
    def get_card_name(cls) -> str:
        return "Banishing Light"
