"""
MTG Engine Package
"""

from .actions_system import Action
from .deck_system import DeckConfiguration
from .game_setup import GameSetupManager
# Export main classes for easy importing
from .game_state import GameState, GameEngine
from .player_system import Player

__all__ = [
    'GameState', 'GameEngine', 'GameSetupManager',
    'DeckConfiguration', 'Player', 'Action'
]