"""
Updated targeting system for the MTG engine.
Now integrates with the prompt system for target selection.
"""

from typing import List, Optional, TYPE_CHECKING, Callable

from engine.core.common_prompts import CommonPrompts
from engine.core.core_types import Zone
from engine.core.prompt_system import prompt_manager, PromptError

if TYPE_CHECKING:
    from engine.core.game_state import GameState
    from engine.core.player_system import Player
    from engine.core.card_system import Card


class TargetingError(Exception):
    """Raised when targeting fails"""
    pass


class TargetFilter:
    """Defines what can be targeted"""

    def __init__(self, description: str, validator: Callable[[Card, Player, GameState], bool]):
        self.description = description
        self.validator = validator

    def is_valid_target(self, card: Card, caster: Player, game_state: GameState) -> bool:
        """Check if a card is a valid target"""
        return self.validator(card, caster, game_state)


class TargetingSystem:
    """Handles targeting for spells and abilities"""

    @staticmethod
    def create_nonland_permanent_opponent_filter() -> TargetFilter:
        """Create filter for 'target nonland permanent an opponent controls'"""

        def validator(card: Card, caster: Player, game_state: GameState) -> bool:
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

        def validator(card: Card, caster: Player, game_state: GameState) -> bool:
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
    def create_any_creature_filter() -> TargetFilter:
        """Create filter for 'target creature'"""

        def validator(card: Card, caster: Player, game_state: GameState) -> bool:
            # Must be on battlefield
            if card.zone != Zone.BATTLEFIELD:
                return False
            # Must be a creature
            if not card.is_creature():
                return False
            return True

        return TargetFilter("target creature", validator)

    @staticmethod
    def create_creature_opponent_controls_filter() -> TargetFilter:
        """Create filter for 'target creature an opponent controls'"""

        def validator(card: Card, caster: Player, game_state: GameState) -> bool:
            # Must be on battlefield
            if card.zone != Zone.BATTLEFIELD:
                return False
            # Must be a creature
            if not card.is_creature():
                return False
            # Must be controlled by opponent
            if card.controller == caster:
                return False
            return True

        return TargetFilter("target creature an opponent controls", validator)

    @staticmethod
    def get_valid_targets(game_state: GameState, caster: Player,
                          target_filter: TargetFilter) -> List[Card]:
        """Get all valid targets for a given filter"""
        valid_targets = []

        # Check all cards on all battlefields
        for player in game_state.players:
            for card in player.battlefield:
                if target_filter.is_valid_target(card, caster, game_state):
                    valid_targets.append(card)

        return valid_targets

    @staticmethod
    def find_card_by_id(game_state: GameState, card_id: str) -> Optional[Card]:
        """Find a card by its ID across all zones"""
        for player in game_state.players:
            for zone_cards in [player.battlefield, player.hand, player.graveyard, player.exile, player.library]:
                for card in zone_cards:
                    if card.id == card_id:
                        return card
        return None

    @staticmethod
    def validate_targets(game_state: GameState, caster: Player,
                         target_filter: TargetFilter, target_ids: List[str]) -> List[Card]:
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

    @staticmethod
    def request_targets(game_state: GameState, caster: Player, target_filter: TargetFilter,
                       spell_name: str = "spell", num_targets: int = 1) -> List[Card]:
        """
        Request targets from the caster using the prompt system

        Args:
            game_state: Current game state
            caster: Player casting the spell
            target_filter: Filter defining valid targets
            spell_name: Name of spell for prompt display
            num_targets: Number of targets required

        Returns:
            List of selected target cards

        Raises:
            TargetingError: If targeting fails or no valid targets
        """
        # Get all valid targets
        valid_targets = TargetingSystem.get_valid_targets(game_state, caster, target_filter)

        if not valid_targets:
            raise TargetingError(f"No valid targets for {spell_name}: {target_filter.description}")

        if num_targets > len(valid_targets):
            raise TargetingError(f"Not enough valid targets (need {num_targets}, found {len(valid_targets)})")

        # Create prompt for target selection
        if num_targets == 1:
            prompt = CommonPrompts.create_target_prompt(
                title=f"Choose Target for {spell_name}",
                description=f"Choose a target for {spell_name}.\nTarget requirement: {target_filter.description}",
                valid_targets=valid_targets
            )
        else:
            # Convert to multi-choice for multiple targets
            prompt = CommonPrompts.create_card_choice_prompt(
                title=f"Choose Targets for {spell_name}",
                description=f"Choose {num_targets} targets for {spell_name}.\nTarget requirement: {target_filter.description}",
                cards=valid_targets,
                min_choices=num_targets,
                max_choices=num_targets
            )

        # Request targets from agent
        try:
            response = prompt_manager.request_prompt(game_state, caster, prompt)

            # Validate and return selected targets
            selected_targets = []
            for target_id in response.selected_ids:
                target_card = TargetingSystem.find_card_by_id(game_state, target_id)
                if target_card and target_card in valid_targets:
                    selected_targets.append(target_card)
                else:
                    raise TargetingError(f"Invalid target selection: {target_id}")

            if len(selected_targets) != num_targets:
                raise TargetingError(f"Expected {num_targets} targets, got {len(selected_targets)}")

            return selected_targets

        except PromptError as e:
            raise TargetingError(f"Failed to get targets from agent: {e}")

    @staticmethod
    def request_single_target(game_state: GameState, caster: Player, target_filter: TargetFilter,
                             spell_name: str = "spell") -> Card:
        """Request a single target - convenience method"""
        targets = TargetingSystem.request_targets(game_state, caster, target_filter, spell_name, 1)
        return targets[0]


# Singleton targeting system
targeting_system = TargetingSystem()
