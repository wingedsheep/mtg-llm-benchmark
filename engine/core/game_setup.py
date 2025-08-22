"""
Updated game setup system for the MTG engine.
Now uses the integrated prompt system instead of external callbacks.
"""

from typing import List, TYPE_CHECKING

from engine.core.coinflip_system import coinflip_system
from engine.core.deck_system import DeckConfiguration, deck_system
from engine.core.display_system import game_logger
from engine.core.mulligan_system import create_mulligan_system

if TYPE_CHECKING:
    from engine.core.player_system import Player
    from engine.core.game_state import GameState


class GameSetupManager:
    """Manages the complete game setup process using the prompt system"""

    def __init__(self):
        self.deck_system = deck_system
        self.mulligan_system = create_mulligan_system()
        self.coinflip_system = coinflip_system

    def setup_game(self, players: List[Player], game_state: GameState = None,
                   interactive: bool = False) -> int:
        """
        Complete game setup process using prompt system

        Args:
            players: List of players to setup
            game_state: Game state for prompts (if None, will skip mulligan phase)
            interactive: If True, use interactive decision making where possible

        Returns:
            Index of the starting player
        """
        game_logger.log_event("=== GAME SETUP ===")

        # 1. Shuffle all decks
        self._shuffle_all_decks(players)

        # 2. Determine starting player
        starting_player_index = self.coinflip_system.determine_starting_player(players, interactive)

        # 3. Draw starting hands
        self.mulligan_system.initialize_starting_hands(players)

        # 4. Mulligan phase using prompt system
        if game_state:
            self.mulligan_system.perform_mulligan_phase(players, game_state)
        else:
            game_logger.log_event("Skipping mulligan phase (no game state provided for prompts)")

        game_logger.log_event("Game setup complete")
        return starting_player_index

    def setup_game_with_callbacks(self, players: List[Player],
                                 mulligan_callback=None, scry_callback=None, bottom_callback=None,
                                 interactive: bool = False) -> int:
        """
        DEPRECATED: Setup game with old callback system

        This method exists for backwards compatibility but should not be used in new code.
        Use setup_game() with prompt system instead.
        """
        game_logger.log_event("=== GAME SETUP (DEPRECATED CALLBACK MODE) ===")
        game_logger.log_event("Warning: Using deprecated callback-based setup. Consider migrating to prompt system.")

        # 1. Shuffle all decks
        self._shuffle_all_decks(players)

        # 2. Determine starting player
        starting_player_index = self.coinflip_system.determine_starting_player(players, interactive)

        # 3. Draw starting hands
        self.mulligan_system.initialize_starting_hands(players)

        # 4. Handle mulligan with callbacks if provided
        if mulligan_callback:
            # Create a temporary compatibility layer for old callback system
            self._perform_callback_mulligans(players, mulligan_callback, bottom_callback)
        else:
            game_logger.log_event("Skipping mulligan phase (no callback provided)")

        game_logger.log_event("Game setup complete")
        return starting_player_index

    def _perform_callback_mulligans(self, players, mulligan_callback, bottom_callback):
        """Compatibility layer for old callback-based mulligan system"""

        mulliganing_players = list(players)

        while mulliganing_players:
            current_round_decisions = {}

            for player in mulliganing_players[:]:
                # Get decision from old callback
                decision = mulligan_callback(player)
                current_round_decisions[player] = decision

                if decision.is_keep():
                    # Handle cards to bottom with old callback
                    mulligan_count = self.mulligan_system.get_mulligan_count(player)
                    if mulligan_count > 0 and bottom_callback:
                        card_ids_to_bottom = bottom_callback(player, mulligan_count)
                        if len(card_ids_to_bottom) == mulligan_count:
                            # Find and bottom the cards
                            cards_to_bottom = []
                            for card_id in card_ids_to_bottom:
                                for card in player.hand:
                                    if card.id == card_id:
                                        cards_to_bottom.append(card)
                                        break

                            if len(cards_to_bottom) == mulligan_count:
                                for card in cards_to_bottom:
                                    player.hand.remove(card)
                                    player.library.append(card)
                                    card.zone = self.mulligan_system.deck_system.Zone.LIBRARY

                                card_names = [card.name for card in cards_to_bottom]
                                game_logger.log_event(
                                    f"{player.name} puts {mulligan_count} cards on bottom: {', '.join(card_names)}")
                            else:
                                self.mulligan_system._bottom_cards_randomly(player, mulligan_count)
                        else:
                            self.mulligan_system._bottom_cards_randomly(player, mulligan_count)

                    game_logger.log_event(f"{player.name} keeps their hand of {len(player.hand)} cards")
                    mulliganing_players.remove(player)

                elif decision.is_mulligan():
                    self.mulligan_system._perform_mulligan(player)

            # Log decisions
            for player, decision in current_round_decisions.items():
                game_logger.log_event(f"{player.name} chooses to {decision.choice}")

    def _shuffle_all_decks(self, players: List[Player]) -> None:
        """Shuffle all player decks"""
        for player in players:
            self.deck_system.shuffle_deck(player.library)

    def create_player_with_deck(self, name: str, deck_config: DeckConfiguration) -> Player:
        """Create a player with a deck from configuration"""
        from engine.core.player_system import Player  # Import here to avoid circular imports

        deck = self.deck_system.create_deck_from_config(deck_config)
        player = Player(name, deck)

        game_logger.log_event(f"Created player {name} with {len(deck)} card deck")
        return player

    def get_mulligan_count(self, player: Player) -> int:
        """Get the number of mulligans a player has taken"""
        return self.mulligan_system.get_mulligan_count(player)

    def reset_for_new_game(self) -> None:
        """Reset the setup manager for a new game"""
        self.mulligan_system.reset_mulligan_counts()


# Singleton setup manager
game_setup_manager = GameSetupManager()
