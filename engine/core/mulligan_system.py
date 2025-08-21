"""
Mulligan system for the MTG engine.
Handles the mulligan phase including starting hands.
Decision making is handled by external agents.
"""

from typing import List, Dict, Callable, Optional, TYPE_CHECKING

from engine.core.core_types import Zone
from engine.core.deck_system import DeckSystem
from engine.core.display_system import game_logger

if TYPE_CHECKING:
    from engine.core.player_system import Player
    from engine.core.card_system import Card


class MulliganDecision:
    """Represents a player's mulligan decision"""

    def __init__(self, choice: str):
        if choice not in ["keep", "mulligan"]:
            raise ValueError("Mulligan choice must be 'keep' or 'mulligan'")
        self.choice = choice

    def is_keep(self) -> bool:
        return self.choice == "keep"

    def is_mulligan(self) -> bool:
        return self.choice == "mulligan"


class MulliganSystem:
    """Handles the mulligan phase of the game"""

    def __init__(self, deck_system: DeckSystem):
        self.deck_system = deck_system
        self.mulligan_counts: Dict[str, int] = {}

    def initialize_starting_hands(self, players: List['Player'], hand_size: int = 7) -> None:
        """Draw starting hands for all players"""
        for player in players:
            self.mulligan_counts[player.name] = 0
            self.deck_system.draw_cards(player.library, player.hand, hand_size)
            game_logger.log_event(f"{player.name} draws {hand_size} cards for starting hand")

    def perform_mulligan_phase(self, players: List['Player'],
                               decision_callback: Callable[['Player'], MulliganDecision],
                               scry_callback: Optional[Callable] = None,
                               bottom_callback: Optional[Callable[['Player', int], List[str]]] = None) -> None:
        """
        Handle the mulligan phase for all players

        Args:
            players: List of players
            decision_callback: Function that takes a player and returns MulliganDecision
            scry_callback: Ignored - kept for compatibility
            bottom_callback: Function that takes (player, num_to_bottom) and returns list of card IDs to bottom
        """
        game_logger.log_event("=== MULLIGAN PHASE ===")

        mulliganing_players = list(players)  # All players start in mulligan phase

        while mulliganing_players:
            current_round_decisions = {}

            # Each player decides simultaneously
            for player in mulliganing_players[:]:  # Copy list to avoid modification during iteration
                decision = decision_callback(player)
                current_round_decisions[player] = decision

                if decision.is_keep():
                    self._finalize_hand(player, bottom_callback)
                    mulliganing_players.remove(player)
                elif decision.is_mulligan():
                    self._perform_mulligan(player)

            # Log decisions
            for player, decision in current_round_decisions.items():
                game_logger.log_event(f"{player.name} chooses to {decision.choice}")

        game_logger.log_event("Mulligan phase complete")

    def get_mulligan_info(self, player: 'Player') -> dict:
        """
        Get information needed for mulligan decision

        Returns:
            Dictionary with hand info, mulligan count, etc.
        """
        hand = player.hand
        mulligan_count = self.mulligan_counts[player.name]

        return {
            'player_name': player.name,
            'hand': hand.copy(),  # Copy to prevent modification
            'hand_size': len(hand),
            'mulligan_count': mulligan_count,
            'max_reasonable_mulligans': 3,  # Suggested limit
            'lands_in_hand': sum(1 for card in hand if card.is_land()),
            'spells_in_hand': sum(1 for card in hand if not card.is_land()),
            'avg_cmc': self._calculate_average_cmc(hand)
        }

    def _calculate_average_cmc(self, hand: List['Card']) -> float:
        """Calculate average converted mana cost of non-land cards in hand"""
        non_lands = [card for card in hand if not card.is_land()]
        if not non_lands:
            return 0.0
        return sum(card.mana_cost.total_cmc() for card in non_lands) / len(non_lands)

    def _perform_mulligan(self, player: 'Player') -> None:
        """Perform a mulligan for a player"""
        self.mulligan_counts[player.name] += 1

        # Put hand back into library
        for card in player.hand:
            card.zone = Zone.LIBRARY
            player.library.append(card)
        player.hand.clear()

        # Shuffle library
        self.deck_system.shuffle_deck(player.library)

        # Always draw 7 cards
        self.deck_system.draw_cards(player.library, player.hand, 7)

        game_logger.log_event(f"{player.name} mulligans (#{self.mulligan_counts[player.name]}) and draws 7 cards")

    def _finalize_hand(self, player: 'Player',
                       bottom_callback: Optional[Callable[['Player', int], List[str]]] = None) -> None:
        """Finalize a player's hand when they choose to keep"""
        mulligan_count = self.mulligan_counts[player.name]

        # Put cards on bottom of library equal to mulligan count
        if mulligan_count > 0:
            if bottom_callback:
                card_ids_to_bottom = bottom_callback(player, mulligan_count)

                if len(card_ids_to_bottom) == mulligan_count:
                    # Find cards by ID and validate they're in hand
                    cards_to_bottom = []
                    for card_id in card_ids_to_bottom:
                        card = self._find_card_in_hand_by_id(player, card_id)
                        if card:
                            cards_to_bottom.append(card)
                        else:
                            game_logger.log_event(f"Card ID {card_id} not found in {player.name}'s hand")

                    if len(cards_to_bottom) == mulligan_count:
                        # Remove cards from hand and put on bottom of library
                        for card in cards_to_bottom:
                            player.hand.remove(card)
                            card.zone = Zone.LIBRARY
                            player.library.append(card)

                        card_names = [card.name for card in cards_to_bottom]
                        game_logger.log_event(
                            f"{player.name} puts {mulligan_count} cards on bottom of library: {', '.join(card_names)}")
                    else:
                        game_logger.log_event(f"Invalid card selection from {player.name}, choosing randomly")
                        self._bottom_cards_randomly(player, mulligan_count)
                else:
                    game_logger.log_event(
                        f"Wrong number of cards from {player.name} (got {len(card_ids_to_bottom)}, need {mulligan_count}), choosing randomly")
                    self._bottom_cards_randomly(player, mulligan_count)
            else:
                # No callback provided, bottom randomly
                self._bottom_cards_randomly(player, mulligan_count)

        game_logger.log_event(f"{player.name} keeps their hand of {len(player.hand)} cards")

    def _find_card_in_hand_by_id(self, player: 'Player', card_id: str) -> Optional['Card']:
        """Find a card in player's hand by its ID"""
        for card in player.hand:
            if card.id == card_id:
                return card
        return None

    def _bottom_cards_randomly(self, player: 'Player', num_to_bottom: int) -> None:
        """Bottom cards randomly when no callback provided"""
        import random

        cards_to_bottom = random.sample(player.hand, min(num_to_bottom, len(player.hand)))
        for card in cards_to_bottom:
            player.hand.remove(card)
            card.zone = Zone.LIBRARY
            player.library.append(card)

        card_names = [card.name for card in cards_to_bottom]
        game_logger.log_event(
            f"{player.name} puts {len(cards_to_bottom)} cards on bottom of library (random): {', '.join(card_names)}")

    def can_mulligan(self, player: 'Player') -> bool:
        """Check if a player can still mulligan (has cards in hand)"""
        return len(player.hand) > 0

    def get_mulligan_count(self, player: 'Player') -> int:
        """Get the number of mulligans a player has taken"""
        return self.mulligan_counts.get(player.name, 0)

    def reset_mulligan_counts(self) -> None:
        """Reset all mulligan counts (for new game)"""
        self.mulligan_counts.clear()

    def format_mulligan_choice_text(self, player: 'Player') -> str:
        """
        Format text for external agent mulligan decision

        Args:
            player: Player making the decision

        Returns:
            Formatted text describing the mulligan situation
        """
        from engine.core.display_system import game_formatter

        info = self.get_mulligan_info(player)

        lines = []
        lines.append(f"=== MULLIGAN DECISION FOR {player.name.upper()} ===")
        lines.append(f"Mulligan count: {info['mulligan_count']}")
        lines.append(f"Current hand size: {info['hand_size']}")
        lines.append("")

        lines.append("Current hand:")
        for i, card in enumerate(info['hand']):
            card_text = game_formatter.format_compact_card(card)
            lines.append(f"{i + 1}. {card_text} [ID: {card.id[:8]}]")

        lines.append("")
        lines.append(f"Hand composition: {info['lands_in_hand']} lands, {info['spells_in_hand']} spells")
        lines.append(f"Average CMC of spells: {info['avg_cmc']:.1f}")
        lines.append("")

        if info['mulligan_count'] > 0:
            lines.append(
                f"If you keep this hand, you will choose {info['mulligan_count']} cards by ID to put on bottom of library.")

        lines.append("Choose: 'keep' or 'mulligan'")

        return "\n".join(lines)


def create_mulligan_system() -> MulliganSystem:
    """Create a new mulligan system with dependencies"""
    from engine.core.deck_system import deck_system
    return MulliganSystem(deck_system)
