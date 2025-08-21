"""
Game setup system for the MTG engine.
Orchestrates the complete game initialization process including deck creation,
coinflip, and mulligan phases.
"""

from typing import List, TYPE_CHECKING

from gameplay.engine.coinflip_system import coinflip_system
from gameplay.engine.deck_system import DeckConfiguration, deck_system
from gameplay.engine.display_system import game_logger
from gameplay.engine.mulligan_system import create_mulligan_system

if TYPE_CHECKING:
    from gameplay.engine.player_system import Player

class GameSetupManager:
    """Manages the complete game setup process"""

    def __init__(self):
        self.deck_system = deck_system
        self.mulligan_system = create_mulligan_system()
        self.coinflip_system = coinflip_system

    def setup_game(self, players: List['Player'],
                   mulligan_callback=None, scry_callback=None, bottom_callback=None,
                   interactive: bool = False) -> int:
        """
        Complete game setup process

        Args:
            players: List of players to setup
            mulligan_callback: Function for making mulligan decisions
            scry_callback: Function for making scry decisions
            bottom_callback: Function for choosing cards to put on bottom
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

        # 4. Mulligan phase (only if callback provided)
        if mulligan_callback:
            self.mulligan_system.perform_mulligan_phase(players, mulligan_callback, scry_callback, bottom_callback)
        else:
            game_logger.log_event("Skipping mulligan phase (no callback provided)")

        game_logger.log_event("Game setup complete")
        return starting_player_index

    def _shuffle_all_decks(self, players: List['Player']) -> None:
        """Shuffle all player decks"""
        for player in players:
            self.deck_system.shuffle_deck(player.library)

    def create_player_with_deck(self, name: str, deck_config: DeckConfiguration) -> 'Player':
        """Create a player with a deck from configuration"""
        from gameplay.engine.player_system import Player  # Import here to avoid circular imports

        deck = self.deck_system.create_deck_from_config(deck_config)
        player = Player(name, deck)

        game_logger.log_event(f"Created player {name} with {len(deck)} card deck")
        return player

    def get_mulligan_count(self, player: 'Player') -> int:
        """Get the number of mulligans a player has taken"""
        return self.mulligan_system.get_mulligan_count(player)

    def reset_for_new_game(self) -> None:
        """Reset the setup manager for a new game"""
        self.mulligan_system.reset_mulligan_counts()

# Singleton setup manager
game_setup_manager = GameSetupManager()
