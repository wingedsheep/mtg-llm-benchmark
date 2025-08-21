"""
Spell resolution system for the MTG engine.
Handles spells on the stack and their resolution.
"""

from typing import List, TYPE_CHECKING

from engine.core.core_types import Zone
from engine.core.display_system import game_logger

if TYPE_CHECKING:
    from engine.core.game_state import GameState
    from engine.core.player_system import Player
    from engine.core.card_system import Card


class StackObject:
    """Represents a spell or ability on the stack"""

    def __init__(self, source_card: 'Card', caster: 'Player', targets: List['Card'] = None):
        self.source_card = source_card
        self.caster = caster
        self.targets = targets or []

    def resolve(self, game_state: 'GameState') -> bool:
        """Resolve this stack object"""
        try:
            # Call the card's resolve method
            if hasattr(self.source_card, 'resolve_spell'):
                return self.source_card.resolve_spell(game_state, self.caster, self.targets)
            else:
                # Default resolution for cards without custom resolve
                return self._default_resolve(game_state)
        except Exception as e:
            game_logger.log_event(f"Error resolving {self.source_card.name}: {e}")
            return False

    def _default_resolve(self, game_state: 'GameState') -> bool:
        """Default resolution - just put spell in graveyard"""
        if self.source_card.zone == Zone.STACK:
            self.caster.graveyard.append(self.source_card)
            self.source_card.zone = Zone.GRAVEYARD
        return True


class SpellSystem:
    """Handles spell casting and resolution"""

    @staticmethod
    def cast_spell_with_targets(game_state: 'GameState', caster: 'Player',
                               spell: 'Card', target_ids: List[str] = None) -> bool:
        """Cast a spell with targets"""
        # Validate spell can be cast
        if not caster.can_cast_spell(spell):
            return False

        # Handle targeting if spell requires targets
        targets = []
        if hasattr(spell, 'get_target_filter') and spell.get_target_filter():
            from engine.core.targeting_system import targeting_system

            target_filter = spell.get_target_filter()
            if target_ids:
                try:
                    targets = targeting_system.validate_targets(game_state, caster, target_filter, target_ids)
                except Exception as e:
                    game_logger.log_event(f"Invalid targets for {spell.name}: {e}")
                    return False
            else:
                # Check if targets are required
                valid_targets = targeting_system.get_valid_targets(game_state, caster, target_filter)
                if valid_targets:  # Targets exist but none provided
                    game_logger.log_event(f"{spell.name} requires targets but none provided")
                    return False

        # Tap lands for mana if needed
        if not caster.tap_lands_for_spell(spell):
            game_logger.log_event(f"Cannot tap enough lands to cast {spell.name}")
            return False

        # Pay mana cost
        if not caster.mana_pool.pay_cost(spell.mana_cost):
            game_logger.log_event(f"Cannot pay mana cost for {spell.name}")
            return False

        # Remove from hand
        caster.hand.remove(spell)
        game_logger.log_event(f"{caster.name} successfully cast {spell.name} (removed from hand)")

        # Handle different spell types
        if spell.is_creature():
            # Creatures go directly to battlefield
            caster.battlefield.append(spell)
            spell.zone = Zone.BATTLEFIELD
            spell.controller = caster
            spell.enters_battlefield()

            game_logger.log_event(f"{spell.name} enters the battlefield")

            # Trigger ETB effects
            from engine.core.core_types import GameEvent
            etb_event = GameEvent("enters_battlefield", card=spell)
            game_state.trigger_manager.check_triggers(etb_event, game_state)

        else:
            # Other spells go on stack
            spell.zone = Zone.STACK
            stack_object = StackObject(spell, caster, targets)
            game_state.stack.append(stack_object)

            game_logger.log_event(f"{caster.name} casts {spell.name} (on stack)")
            if targets:
                target_names = [t.name for t in targets]
                game_logger.log_event(f"  targeting: {', '.join(target_names)}")

        return True

    @staticmethod
    def resolve_top_of_stack(game_state: 'GameState') -> bool:
        """Resolve the top spell/ability on the stack"""
        if not game_state.stack:
            return False

        stack_object = game_state.stack.pop()  # Remove from top
        game_logger.log_event(f"Resolving {stack_object.source_card.name}")

        return stack_object.resolve(game_state)


# Singleton spell system
spell_system = SpellSystem()
