"""
Fixed game state management for the MTG engine.
Ensures proper turn structure, phase progression, and game flow.
FIXED: Resets combat declaration flags when entering combat phases.
"""

from typing import List, Optional, Any

from gameplay.engine.actions_system import Action, action_generator, action_validator
from gameplay.engine.core_types import Phase, GameEvent
from gameplay.engine.display_system import game_formatter, game_logger
from gameplay.engine.effects_system import TriggerManager
from gameplay.engine.player_system import Player, PlayerManager


class GameState:
    """Main game state class that manages the entire game"""

    def __init__(self, players: List[Player]):
        # Player management
        self.player_manager = PlayerManager(players)
        self.players = players

        # Turn and phase management
        self.turn_number = 1
        self.active_player_index = 0
        self.priority_player_index = 0
        self.phase = Phase.UNTAP

        # Game state
        self.stack: List[Any] = []
        self.game_over = False
        self.winner: Optional[Player] = None

        # Systems
        self.trigger_manager = TriggerManager()

        # Initialize game
        self._setup_game()

    def _setup_game(self):
        """Initialize the game"""
        # Log game start
        game_logger.new_turn(1)
        game_logger.log_event("Game started")

        # Start first turn
        self._start_turn()

    @property
    def active_player(self) -> Player:
        """Get the active player"""
        return self.players[self.active_player_index]

    @property
    def non_active_player(self) -> Player:
        """Get the non-active player"""
        return self.players[1 - self.active_player_index]

    @property
    def priority_player(self) -> Player:
        """Get the player with priority"""
        return self.players[self.priority_player_index]

    def get_legal_actions(self, player: Player) -> List[Action]:
        """Get all legal actions for a player"""
        if self.game_over:
            return []

        # Only the player with priority can take actions
        if player != self.priority_player:
            return []

        actions = action_generator.get_legal_actions(self, player)

        # Filter actions through validator
        legal_actions = []
        for action in actions:
            if action_validator.is_action_legal(action, self, player):
                legal_actions.append(action)

        # Auto-pass if only action is passing priority
        if len(legal_actions) == 1 and legal_actions[0].action_type == "pass":
            game_logger.log_event(f"{player.name} has no actions available - auto-passing")
            self.pass_priority()
            return []

        return legal_actions

    def execute_action(self, player: Player, action: Action) -> bool:
        """Execute a player action"""
        if self.game_over:
            return False

        if player != self.priority_player:
            return False

        if not action_validator.is_action_legal(action, self, player):
            return False

        # Log the action
        game_logger.log_action(player.name, action.description)

        # Execute the action
        try:
            result = action.execute(self)

            # Check for triggered abilities
            self.trigger_manager.resolve_triggers(self)

            # Check for state-based actions
            self._check_state_based_actions()

            # Check win conditions
            self._check_win_conditions()

            # After action execution, check if current player has any remaining actions
            # If not, auto-pass to keep the game flowing
            if not self.game_over:
                remaining_actions = action_generator.get_legal_actions(self, self.priority_player)
                legal_remaining = [a for a in remaining_actions if action_validator.is_action_legal(a, self, self.priority_player)]

                if len(legal_remaining) == 1 and legal_remaining[0].action_type == "pass":
                    game_logger.log_event(f"{self.priority_player.name} has no more actions - auto-passing")
                    self.pass_priority()

            return True

        except Exception as e:
            game_logger.log_event(f"Error executing action: {e}")
            return False

    def pass_priority(self):
        """Pass priority to the next player"""
        current_player = self.priority_player.name

        # If stack is empty and all players pass, move to next phase
        if not self.stack:
            next_priority = 1 - self.priority_player_index

            if next_priority == self.active_player_index:
                # Priority has gone around - move to next phase
                game_logger.log_event(f"Priority passed from {current_player} - all players passed, moving to next phase")
                self._next_phase()
            else:
                self.priority_player_index = next_priority
                new_player = self.priority_player.name
                game_logger.log_event(f"Priority passed: {current_player} → {new_player}")
        else:
            # Handle stack resolution (simplified for now)
            self.priority_player_index = 1 - self.priority_player_index
            new_player = self.priority_player.name
            game_logger.log_event(f"Priority passed (stack resolution): {current_player} → {new_player}")

    def _next_phase(self):
        """Move to the next phase"""
        # Define the correct phase order
        phase_order = [
            Phase.UNTAP,
            Phase.UPKEEP,
            Phase.DRAW,
            Phase.MAIN1,
            Phase.COMBAT_BEGIN,
            Phase.COMBAT_DECLARE_ATTACKERS,
            Phase.COMBAT_DECLARE_BLOCKERS,
            Phase.COMBAT_DAMAGE,
            Phase.COMBAT_END,
            Phase.MAIN2,
            Phase.END,
            Phase.CLEANUP
        ]

        current_index = phase_order.index(self.phase)

        if current_index + 1 < len(phase_order):
            old_phase = self.phase
            self.phase = phase_order[current_index + 1]
            game_logger.log_event(f"Phase transition: {old_phase.value} → {self.phase.value}")
            self._enter_phase()
        else:
            # End of turn
            self._end_turn()

    def _enter_phase(self):
        """Handle entering a new phase"""
        game_logger.log_event(f"=== ENTERING {self.phase.value.upper()} PHASE ===")
        game_logger.log_event(f"Active player: {self.active_player.name}, Priority: {self.priority_player.name}")

        # Reset priority to active player for new phase (except blocking phase)
        if self.phase != Phase.COMBAT_DECLARE_BLOCKERS:
            self.priority_player_index = self.active_player_index

        # Phase-specific actions
        if self.phase == Phase.UNTAP:
            self.active_player.untap_step()
            # Untap step has no priority - automatically advance
            game_logger.log_event("Untap step complete - no priority, advancing to upkeep")
            self._next_phase()
            return

        elif self.phase == Phase.UPKEEP:
            self.active_player.upkeep_step()
            # Check if there are any upkeep triggers or actions
            actions = self.get_legal_actions(self.priority_player)
            if not actions:
                game_logger.log_event("No upkeep actions - auto-advancing to draw step")
                self._next_phase()
                return

        elif self.phase == Phase.DRAW:
            # First player doesn't draw on their very first turn (turn 1)
            # But second player draws on their first turn (which is turn 2)
            should_draw = not (self.turn_number == 1 and self.active_player.turn_count == 0)

            if should_draw:
                self.active_player.draw_step()
                game_logger.log_event(f"{self.active_player.name} draws a card")
            else:
                game_logger.log_event(f"{self.active_player.name} skips draw (first turn)")

            # Draw step typically has no priority - automatically advance
            game_logger.log_event("Draw step complete - advancing to first main phase")
            self._next_phase()
            return

        elif self.phase == Phase.COMBAT_BEGIN:
            # Reset combat flags when starting a new combat
            action_generator.reset_combat_flags()

            # Beginning of combat - check if active player wants to do anything
            actions = self.get_legal_actions(self.active_player)
            if not actions:
                game_logger.log_event("No beginning of combat actions - advancing to declare attackers")
                self._next_phase()
                return

        elif self.phase == Phase.COMBAT_DECLARE_BLOCKERS:
            # Priority goes to defending player for blocking
            self.priority_player_index = 1 - self.active_player_index

        elif self.phase == Phase.COMBAT_DAMAGE:
            # Import here to avoid circular imports
            from gameplay.engine.combat_system import combat_system
            combat_system.resolve_combat_damage(self)
            # Damage step typically auto-advances
            game_logger.log_event("Combat damage resolved - advancing to end of combat")
            self._next_phase()
            return

        elif self.phase == Phase.COMBAT_END:
            # Import here to avoid circular imports
            from gameplay.engine.combat_system import combat_system
            combat_system.end_combat(self)
            # End of combat typically auto-advances
            game_logger.log_event("End of combat - advancing to second main phase")
            self._next_phase()
            return

        elif self.phase == Phase.END:
            # End step - check for end step triggers
            actions = self.get_legal_actions(self.priority_player)
            if not actions:
                game_logger.log_event("No end step actions - advancing to cleanup")
                self._next_phase()
                return

        elif self.phase == Phase.CLEANUP:
            self.active_player.cleanup_step()
            # Cleanup step has no priority - automatically advance
            game_logger.log_event("Cleanup step complete - ending turn")
            self._end_turn()
            return

    def _start_turn(self):
        """Start a new turn"""
        game_logger.new_turn(self.turn_number)
        game_logger.log_event(f"=== {self.active_player.name.upper()}'S TURN {self.turn_number} BEGINS ===")

        # Reset player state
        self.active_player.start_turn()

        # Start with untap phase
        self.phase = Phase.UNTAP
        self.priority_player_index = self.active_player_index
        self._enter_phase()

    def _end_turn(self):
        """End the current turn"""
        game_logger.log_event(f"=== {self.active_player.name.upper()}'S TURN ENDS ===")

        # Move to next player
        self.active_player_index = 1 - self.active_player_index
        self.priority_player_index = self.active_player_index
        self.turn_number += 1

        # Start next turn
        self._start_turn()

    def _check_state_based_actions(self):
        """Check and apply state-based actions"""
        # Import here to avoid circular imports
        from gameplay.engine.combat_system import combat_system

        changes_made = True
        while changes_made:
            changes_made = combat_system.check_creature_death(self)

    def _check_win_conditions(self):
        """Check if any player has won"""
        alive_players = [p for p in self.players if p.is_alive()]

        if len(alive_players) <= 1:
            self.game_over = True
            if alive_players:
                self.winner = alive_players[0]
                game_logger.log_event(f"{self.winner.name} wins the game!")
            else:
                game_logger.log_event("Game ends in a draw!")

    def trigger_event(self, event: GameEvent):
        """Trigger a game event"""
        self.trigger_manager.check_triggers(event, self)

    def get_game_state_text(self, perspective_player: Player) -> str:
        """Get formatted game state from player's perspective"""
        return game_formatter.format_game_state(self, perspective_player)

    def get_actions_text(self, player: Player) -> str:
        """Get formatted available actions for a player"""
        actions = self.get_legal_actions(player)
        return game_formatter.format_actions(actions)

    def is_game_over(self) -> bool:
        """Check if the game is over"""
        return self.game_over

    def get_winner(self) -> Optional[Player]:
        """Get the winner if game is over"""
        return self.winner

    def get_game_log(self) -> str:
        """Get the game log"""
        return game_logger.get_full_log()

    def get_current_phase_info(self) -> str:
        """Get current phase information for debugging"""
        return f"Turn {self.turn_number} | {self.phase.value.title()} Phase | Active: {self.active_player.name} | Priority: {self.priority_player.name}"

    def save_state(self) -> dict:
        """Save current game state (for AI analysis, etc.)"""
        return {
            'turn_number': self.turn_number,
            'active_player': self.active_player.name,
            'priority_player': self.priority_player.name,
            'phase': self.phase.value,
            'players': [
                {
                    'name': p.name,
                    'life': p.life,
                    'hand_size': len(p.hand),
                    'battlefield_size': len(p.battlefield),
                    'mana_pool': p.mana_pool.mana.copy()
                }
                for p in self.players
            ],
            'game_over': self.game_over,
            'winner': self.winner.name if self.winner else None
        }


class GameEngine:
    """High-level game engine interface"""

    def __init__(self):
        self.current_game: Optional[GameState] = None

    def start_new_game(self, players: List[Player]) -> GameState:
        """Start a new game with the given players"""
        self.current_game = GameState(players)
        return self.current_game

    def get_game_state(self, player: Player) -> str:
        """Get game state from player's perspective"""
        if not self.current_game:
            return "No game in progress"

        return self.current_game.get_game_state_text(player)

    def get_legal_actions(self, player: Player) -> List[Action]:
        """Get legal actions for a player"""
        if not self.current_game:
            return []

        return self.current_game.get_legal_actions(player)

    def execute_action(self, player: Player, action_index: int) -> bool:
        """Execute an action by index"""
        if not self.current_game:
            return False

        actions = self.get_legal_actions(player)
        if 0 <= action_index < len(actions):
            return self.current_game.execute_action(player, actions[action_index])

        return False

    def is_game_over(self) -> bool:
        """Check if current game is over"""
        return self.current_game is None or self.current_game.is_game_over()

    def get_winner(self) -> Optional[Player]:
        """Get winner of current game"""
        if self.current_game:
            return self.current_game.get_winner()
        return None


# Singleton game engine
game_engine = GameEngine()
