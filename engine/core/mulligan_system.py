"""
Updated mulligan system for the MTG engine.
Now uses the prompt system for all mulligan decisions.
"""

from typing import List, Dict, TYPE_CHECKING

from engine.core.common_prompts import CommonPrompts, PromptResponseHelper
from engine.core.core_types import Zone
from engine.core.deck_system import DeckSystem
from engine.core.display_system import game_logger
from engine.core.prompt_system import prompt_manager, PromptError

if TYPE_CHECKING:
    from engine.core.player_system import Player
    from engine.core.card_system import Card


class MulliganSystem:
    """Handles the mulligan phase of the game using the prompt system"""

    def __init__(self, deck_system: DeckSystem):
        self.deck_system = deck_system
        self.mulligan_counts: Dict[str, int] = {}

    def initialize_starting_hands(self, players: List[Player], hand_size: int = 7) -> None:
        """Draw starting hands for all players"""
        for player in players:
            self.mulligan_counts[player.name] = 0
            self.deck_system.draw_cards(player.library, player.hand, hand_size)
            game_logger.log_event(f"{player.name} draws {hand_size} cards for starting hand")

    def perform_mulligan_phase(self, players: List[Player], game_state) -> None:
        """
        Handle the mulligan phase for all players using prompt system

        Args:
            players: List of players
            game_state: Game state (for prompts)
        """
        game_logger.log_event("=== MULLIGAN PHASE ===")

        mulliganing_players = list(players)  # All players start in mulligan phase

        while mulliganing_players:
            current_round_decisions = {}

            # Each player decides simultaneously
            for player in mulliganing_players[:]:  # Copy list to avoid modification during iteration
                try:
                    keep_hand = self._request_mulligan_decision(game_state, player)
                    current_round_decisions[player] = keep_hand

                    if keep_hand:
                        self._finalize_hand(game_state, player)
                        mulliganing_players.remove(player)
                    else:
                        self._perform_mulligan(player)

                except PromptError as e:
                    game_logger.log_event(f"Mulligan prompt failed for {player.name}: {e}, keeping hand")
                    self._finalize_hand(game_state, player)
                    mulliganing_players.remove(player)
                    current_round_decisions[player] = True

            # Log decisions
            for player, keep_decision in current_round_decisions.items():
                decision_text = "keep" if keep_decision else "mulligan"
                game_logger.log_event(f"{player.name} chooses to {decision_text}")

        game_logger.log_event("Mulligan phase complete")

    def _request_mulligan_decision(self, game_state, player: Player) -> bool:
        """Request mulligan decision from player using prompt system"""
        mulligan_count = self.mulligan_counts[player.name]
        lands_in_hand = sum(1 for card in player.hand if card.is_land())
        spells_in_hand = sum(1 for card in player.hand if not card.is_land())

        prompt = CommonPrompts.create_mulligan_prompt(player, mulligan_count, lands_in_hand, spells_in_hand)
        response = prompt_manager.request_prompt(game_state, player, prompt)

        return PromptResponseHelper.is_yes_response(response)

    def get_mulligan_info(self, player: Player) -> dict:
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

    def _calculate_average_cmc(self, hand: List[Card]) -> float:
        """Calculate average converted mana cost of non-land cards in hand"""
        non_lands = [card for card in hand if not card.is_land()]
        if not non_lands:
            return 0.0
        return sum(card.mana_cost.total_cmc() for card in non_lands) / len(non_lands)

    def _perform_mulligan(self, player: Player) -> None:
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

    def _finalize_hand(self, game_state, player: Player) -> None:
        """Finalize a player's hand when they choose to keep"""
        mulligan_count = self.mulligan_counts[player.name]

        # Put cards on bottom of library equal to mulligan count
        if mulligan_count > 0:
            try:
                selected_cards = self._request_cards_to_bottom(game_state, player, mulligan_count)

                if len(selected_cards) == mulligan_count:
                    # Remove cards from hand and put on bottom of library
                    for card in selected_cards:
                        player.hand.remove(card)
                        card.zone = Zone.LIBRARY
                        player.library.append(card)

                    card_names = [card.name for card in selected_cards]
                    game_logger.log_event(
                        f"{player.name} puts {mulligan_count} cards on bottom of library: {', '.join(card_names)}")
                else:
                    game_logger.log_event(f"Invalid card selection from {player.name}, choosing randomly")
                    self._bottom_cards_randomly(player, mulligan_count)

            except PromptError as e:
                game_logger.log_event(f"Cards to bottom prompt failed for {player.name}: {e}, choosing randomly")
                self._bottom_cards_randomly(player, mulligan_count)

        game_logger.log_event(f"{player.name} keeps their hand of {len(player.hand)} cards")

    def _request_cards_to_bottom(self, game_state, player: Player, num_to_bottom: int) -> List[Card]:
        """Request which cards to put on bottom using prompt system"""
        prompt = CommonPrompts.create_cards_to_bottom_prompt(player, num_to_bottom)
        response = prompt_manager.request_prompt(game_state, player, prompt)

        # Convert selected IDs back to cards
        selected_cards = []
        for card_id in response.selected_ids:
            for card in player.hand:
                if card.id == card_id:
                    selected_cards.append(card)
                    break

        return selected_cards

    def _bottom_cards_randomly(self, player: Player, num_to_bottom: int) -> None:
        """Bottom cards randomly when prompt fails"""
        import random

        cards_to_bottom = random.sample(player.hand, min(num_to_bottom, len(player.hand)))
        for card in cards_to_bottom:
            player.hand.remove(card)
            card.zone = Zone.LIBRARY
            player.library.append(card)

        card_names = [card.name for card in cards_to_bottom]
        game_logger.log_event(
            f"{player.name} puts {len(cards_to_bottom)} cards on bottom of library (random): {', '.join(card_names)}")

    def can_mulligan(self, player: Player) -> bool:
        """Check if a player can still mulligan (has cards in hand)"""
        return len(player.hand) > 0

    def get_mulligan_count(self, player: Player) -> int:
        """Get the number of mulligans a player has taken"""
        return self.mulligan_counts.get(player.name, 0)

    def reset_mulligan_counts(self) -> None:
        """Reset all mulligan counts (for new game)"""
        self.mulligan_counts.clear()

    def format_mulligan_choice_text(self, player: Player) -> str:
        """
        Format text for external agent mulligan decision
        DEPRECATED: Use prompt system instead
        """
        info = self.get_mulligan_info(player)

        lines = []
        lines.append(f"=== MULLIGAN DECISION FOR {player.name.upper()} ===")
        lines.append(f"Mulligan count: {info['mulligan_count']}")
        lines.append(f"Current hand size: {info['hand_size']}")
        lines.append("")

        lines.append("Current hand:")
        for i, card in enumerate(info['hand']):
            from engine.core.display_system import game_formatter
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
