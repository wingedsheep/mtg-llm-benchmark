"""
Scry system for the MTG engine.
Handles scry mechanics - looking at top cards and choosing which to bottom.
"""

from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

from gameplay.engine.deck_system import DeckSystem
from gameplay.engine.display_system import game_logger

if TYPE_CHECKING:
    from gameplay.engine.player_system import Player
    from gameplay.engine.card_system import Card


@dataclass
class ScryChoice:
    """Represents a player's choice during scry"""
    cards_to_bottom: List['Card']
    cards_to_top: List['Card']  # In order from top to bottom

    def validate(self, available_cards: List['Card']) -> bool:
        """Validate that the choice is legal"""
        all_chosen = self.cards_to_bottom + self.cards_to_top

        # Check that all cards are accounted for
        if len(all_chosen) != len(available_cards):
            return False

        # Check that no card appears twice
        if len(set(card.id for card in all_chosen)) != len(all_chosen):
            return False

        # Check that all cards are from the available cards
        available_ids = {card.id for card in available_cards}
        chosen_ids = {card.id for card in all_chosen}

        return chosen_ids == available_ids


class ScrySystem:
    """Handles scry mechanics"""

    def __init__(self, deck_system: DeckSystem):
        self.deck_system = deck_system

    def initiate_scry(self, player: 'Player', scry_amount: int) -> Optional[List['Card']]:
        """
        Start a scry - look at top N cards from library

        Args:
            player: Player performing the scry
            scry_amount: Number of cards to look at

        Returns:
            List of cards being scried, or None if no cards available
        """
        if scry_amount <= 0 or len(player.library) == 0:
            game_logger.log_event(f"{player.name} scries 0 (no cards available)")
            return None

        # Look at top cards
        cards_to_scry = []
        look_amount = min(scry_amount, len(player.library))

        # Remove cards from top of library temporarily
        for _ in range(look_amount):
            card = player.library.pop(0)
            cards_to_scry.append(card)

        game_logger.log_event(f"{player.name} scries {look_amount} (looking at top {look_amount} cards)")

        return cards_to_scry

    def complete_scry(self, player: 'Player', scry_cards: List['Card'], choice: ScryChoice) -> bool:
        """
        Complete a scry with the player's choice

        Args:
            player: Player performing the scry
            scry_cards: Cards that were being scried
            choice: Player's choice of what to do with the cards

        Returns:
            True if successful, False if invalid choice
        """
        if not choice.validate(scry_cards):
            game_logger.log_event(f"Invalid scry choice from {player.name}")
            return False

        # Put chosen cards on bottom (in any order)
        if choice.cards_to_bottom:
            self.deck_system.put_cards_bottom(player.library, choice.cards_to_bottom)
            game_logger.log_event(f"{player.name} puts {len(choice.cards_to_bottom)} cards on bottom of library")

        # Put remaining cards back on top (in specified order)
        if choice.cards_to_top:
            self.deck_system.put_cards_top(player.library, choice.cards_to_top)
            game_logger.log_event(f"{player.name} puts {len(choice.cards_to_top)} cards on top of library")

        return True

    def perform_full_scry(self, player: 'Player', scry_amount: int, choice_callback) -> bool:
        """
        Perform a complete scry with external choice callback

        Args:
            player: Player performing the scry
            scry_amount: Number of cards to scry
            choice_callback: Function that takes (player, cards) and returns ScryChoice

        Returns:
            True if scry was performed, False if no cards to scry
        """
        scry_cards = self.initiate_scry(player, scry_amount)

        if scry_cards is None:
            return False

        # Get choice from external agent
        choice = choice_callback(player, scry_cards)

        # Complete the scry
        success = self.complete_scry(player, scry_cards, choice)

        if not success:
            # If choice was invalid, put cards back on top in original order
            self.deck_system.put_cards_top(player.library, scry_cards)
            game_logger.log_event(f"Scry failed, cards returned to top of library")

        return success

    def get_scry_preview(self, player: 'Player', scry_amount: int) -> List['Card']:
        """
        Preview what a scry would show without actually performing it

        Args:
            player: Player who would scry
            scry_amount: Number of cards that would be looked at

        Returns:
            List of cards that would be seen (doesn't modify library)
        """
        look_amount = min(scry_amount, len(player.library))
        return player.library[:look_amount]

    def format_scry_choice_text(self, player: 'Player', scry_cards: List['Card']) -> str:
        """
        Format text showing scry cards for external agent decision making

        Args:
            player: Player performing the scry
            scry_cards: Cards being scried

        Returns:
            Formatted text describing the scry situation
        """
        from gameplay.engine.display_system import game_formatter

        lines = []
        lines.append(f"{player.name} is scrying {len(scry_cards)} cards:")
        lines.append("")

        for i, card in enumerate(scry_cards):
            card_text = game_formatter.format_compact_card(card)
            lines.append(f"{i + 1}. {card_text}")

        lines.append("")
        lines.append("Choose which cards to put on bottom of library.")
        lines.append("Remaining cards will be put back on top in your chosen order.")

        return "\n".join(lines)


# Helper functions for common scry scenarios
def create_default_scry_choice(scry_cards: List['Card']) -> ScryChoice:
    """Create a default scry choice (put all cards back on top in original order)"""
    return ScryChoice(cards_to_bottom=[], cards_to_top=scry_cards)


def create_bottom_all_scry_choice(scry_cards: List['Card']) -> ScryChoice:
    """Create a scry choice that bottoms all cards"""
    return ScryChoice(cards_to_bottom=scry_cards, cards_to_top=[])


# Factory function
def create_scry_system() -> ScrySystem:
    """Create a new scry system with deck system dependency"""
    from gameplay.engine.deck_system import deck_system
    return ScrySystem(deck_system)


# Singleton scry system
scry_system = create_scry_system()
