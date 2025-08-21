"""
Targeting system for the MTG engine.
Handles target selection and validation for spells and abilities.
"""

from typing import List, Optional, TYPE_CHECKING, Callable

from engine.core.core_types import Zone

if TYPE_CHECKING:
    from engine.core.game_state import GameState
    from engine.core.player_system import Player
    from engine.core.card_system import Card


class TargetingError(Exception):
    """Raised when targeting fails"""
    pass


class TargetFilter:
    """Defines what can be targeted"""

    def __init__(self, description: str, validator: Callable[['Card', 'Player', 'GameState'], bool]):
        self.description = description
        self.validator = validator

    def is_valid_target(self, card: 'Card', caster: 'Player', game_state: 'GameState') -> bool:
        """Check if a card is a valid target"""
        return self.validator(card, caster, game_state)


class TargetingSystem:
    """Handles targeting for spells and abilities"""

    @staticmethod
    def create_nonland_permanent_opponent_filter() -> TargetFilter:
        """Create filter for 'target nonland permanent an opponent controls'"""

        def validator(card: 'Card', caster: 'Player', game_state: 'GameState') -> bool:
            # Must be on battlefield
            if card.zone != Zone.BATTLEFIELD:
                return False
            # Must not be a land
            if card.is_land():
                return False
            # Must be controlled by opponent
            if card.controller == caster:
                return False
            return True

        return TargetFilter("target nonland permanent an opponent controls", validator)

    @staticmethod
    def create_creature_you_control_filter() -> TargetFilter:
        """Create filter for 'target creature you control'"""

        def validator(card: 'Card', caster: 'Player', game_state: 'GameState') -> bool:
            # Must be on battlefield
            if card.zone != Zone.BATTLEFIELD:
                return False
            # Must be a creature
            if not card.is_creature():
                return False
            # Must be controlled by caster
            if card.controller != caster:
                return False
            return True

        return TargetFilter("target creature you control", validator)

    @staticmethod
    def get_valid_targets(game_state: 'GameState', caster: 'Player',
                          target_filter: TargetFilter) -> List['Card']:
        """Get all valid targets for a given filter"""
        valid_targets = []

        # Check all cards on all battlefields
        for player in game_state.players:
            for card in player.battlefield:
                if target_filter.is_valid_target(card, caster, game_state):
                    valid_targets.append(card)

        return valid_targets

    @staticmethod
    def find_card_by_id(game_state: 'GameState', card_id: str) -> Optional['Card']:
        """Find a card by its ID across all zones"""
        for player in game_state.players:
            for zone_cards in [player.battlefield, player.hand, player.graveyard, player.exile, player.library]:
                for card in zone_cards:
                    if card.id == card_id:
                        return card
        return None

    @staticmethod
    def validate_targets(game_state: 'GameState', caster: 'Player',
                         target_filter: TargetFilter, target_ids: List[str]) -> List['Card']:
        """Validate that provided target IDs are legal targets"""
        if not target_ids:
            raise TargetingError("No targets provided")

        targets = []
        for target_id in target_ids:
            card = TargetingSystem.find_card_by_id(game_state, target_id)
            if not card:
                raise TargetingError(f"Card with ID {target_id} not found")

            if not target_filter.is_valid_target(card, caster, game_state):
                raise TargetingError(f"{card.name} is not a valid target: {target_filter.description}")

            targets.append(card)

        return targets


# Singleton targeting system
targeting_system = TargetingSystem()
