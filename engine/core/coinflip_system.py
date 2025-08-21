"""
Coinflip system for the MTG engine.
Handles random game start mechanics and player selection.
"""

import random
from typing import List, TYPE_CHECKING

from engine.core.display_system import game_logger

if TYPE_CHECKING:
    from engine.core.player_system import Player


class CoinflipSystem:
    """Handles coinflip mechanics for game start"""

    @staticmethod
    def coinflip() -> bool:
        """Return True for heads, False for tails"""
        return random.choice([True, False])

    @staticmethod
    def determine_starting_player(players: List['Player'], interactive: bool = False) -> int:
        """
        Determine which player goes first via coinflip

        Args:
            players: List of players
            interactive: If True, winner gets to choose play/draw (not implemented yet)

        Returns:
            Index of the starting player
        """
        if len(players) != 2:
            raise ValueError("Coinflip system currently supports only 2 players")

        winner_index = 0 if CoinflipSystem.coinflip() else 1
        winner = players[winner_index]
        loser = players[1 - winner_index]

        game_logger.log_event(f"Coinflip: {winner.name} wins the flip")

        # For now, winner always chooses to go first
        # In the future, this could be made interactive
        if interactive:
            # TODO: Implement interactive choice
            choice = "play"  # Default choice
        else:
            choice = "play"  # Winner chooses to play first

        if choice == "play":
            game_logger.log_event(f"{winner.name} chooses to play first")
            return winner_index
        else:
            game_logger.log_event(f"{winner.name} chooses to draw first")
            return 1 - winner_index

    @staticmethod
    def random_choice(options: List[any]) -> any:
        """Make a random choice from a list of options"""
        return random.choice(options)

    @staticmethod
    def roll_die(sides: int = 20) -> int:
        """Roll a die with specified number of sides (default d20)"""
        return random.randint(1, sides)


# Singleton coinflip system
coinflip_system = CoinflipSystem()
