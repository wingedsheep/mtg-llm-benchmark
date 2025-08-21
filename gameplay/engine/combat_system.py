"""
Combat system for the MTG engine.
Handles combat damage resolution and creature death.
"""

from typing import TYPE_CHECKING

from gameplay.engine.core_types import GameEvent, Zone
from gameplay.engine.display_system import game_logger

if TYPE_CHECKING:
    from gameplay.engine.game_state import GameState


class CombatSystem:
    """Handles combat mechanics and damage resolution"""

    def __init__(self):
        pass

    def resolve_combat_damage(self, game_state: 'GameState') -> None:
        """Resolve combat damage step"""
        active_player = game_state.active_player
        defending_player = game_state.non_active_player

        # Get all attacking creatures
        attackers = active_player.get_attackers()

        if not attackers:
            game_logger.log_event("No combat damage - no attackers")
            return

        # For simplicity, assume all attackers are unblocked
        total_damage = 0
        for attacker in attackers:
            damage = attacker.current_power()
            total_damage += damage
            game_logger.log_event(f"{attacker.name} deals {damage} damage")

        if total_damage > 0:
            defending_player.lose_life(total_damage)
            game_logger.log_event(f"{defending_player.name} loses {total_damage} life (now at {defending_player.life})")

    def check_creature_death(self, game_state: 'GameState') -> bool:
        """Check for creatures that should die and move them to graveyard"""
        changes_made = False

        for player in game_state.players:
            creatures_to_remove = []

            for creature in player.get_creatures():
                if creature.current_toughness() <= 0:
                    creatures_to_remove.append(creature)

            # Remove dead creatures
            for creature in creatures_to_remove:
                player.battlefield.remove(creature)
                player.graveyard.append(creature)
                creature.zone = Zone.GRAVEYARD
                creature.leaves_battlefield()

                game_logger.log_event(f"{creature.name} dies")

                # Trigger death event
                death_event = GameEvent("dies", card=creature)
                game_state.trigger_manager.check_triggers(death_event, game_state)

                changes_made = True

        return changes_made

    def end_combat(self, game_state: 'GameState') -> None:
        """Clean up combat state at end of combat"""
        for player in game_state.players:
            for creature in player.get_creatures():
                creature.is_attacking = False
                creature.is_blocking = False

        game_logger.log_event("Combat ends")


# Singleton combat system
combat_system = CombatSystem()
