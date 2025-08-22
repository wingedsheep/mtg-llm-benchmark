"""
Display system for the MTG engine.
Handles formatting game state and card information for text-based interface.
"""

from typing import List, TYPE_CHECKING

from engine.core.core_types import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from player_system import Player
    from engine.core.card_system import Card
    from engine.core.actions_system import Action


class GameStateFormatter:
    """Formats game state information for display"""

    def __init__(self):
        pass

    def format_game_state(self, game_state: GameState, perspective_player: Player) -> str:
        """Get complete game state from player's perspective"""
        sections = []

        # Header
        sections.append(self._format_header(game_state))

        # Player's status
        sections.append(self._format_player_status(perspective_player))

        # Player's hand
        sections.append(self._format_hand(perspective_player))

        # Player's battlefield
        sections.append(self._format_battlefield(perspective_player, "YOUR BATTLEFIELD"))

        # Opponent's status
        opponent = self._get_opponent(game_state, perspective_player)
        sections.append(self._format_opponent_status(opponent))

        # Opponent's battlefield
        sections.append(self._format_battlefield(opponent, "OPPONENT'S BATTLEFIELD"))

        # Stack
        if game_state.stack:
            sections.append(self._format_stack(game_state))

        # Remove empty sections and join
        non_empty_sections = [section for section in sections if section.strip()]
        return "\n\n".join(non_empty_sections)

    def _format_header(self, game_state: GameState) -> str:
        """Format game header information"""
        lines = []
        lines.append(f"=== TURN {game_state.turn_number} - {game_state.phase.value.upper()} PHASE ===")
        lines.append(f"Active Player: {game_state.active_player.name}")
        lines.append(f"Priority: {game_state.priority_player.name}")
        return "\n".join(lines)

    def _format_player_status(self, player: Player) -> str:
        """Format player's basic status"""
        lines = []
        lines.append(f"YOUR STATUS ({player.name}):")
        lines.append(f"Life: {player.life}")

        # Mana pool
        mana_display = player.mana_pool.get_display_string()
        lines.append(f"Mana Pool: {mana_display}")

        return "\n".join(lines)

    def _format_opponent_status(self, opponent: Player) -> str:
        """Format opponent's visible status"""
        lines = []
        lines.append(f"OPPONENT STATUS ({opponent.name}):")
        lines.append(f"Life: {opponent.life}")
        lines.append(f"Hand: {len(opponent.hand)} cards")
        return "\n".join(lines)

    def _format_hand(self, player: Player) -> str:
        """Format player's hand"""
        lines = []
        lines.append(f"HAND ({len(player.hand)} cards):")

        if player.hand:
            for i, card in enumerate(player.hand):
                card_text = self.format_card_details(card, show_full=True)
                lines.append(f"{i + 1}. {card_text}")
        else:
            lines.append("  (empty)")

        return "\n".join(lines)

    def _format_battlefield(self, player: Player, title: str) -> str:
        """Format a player's battlefield"""
        lines = []
        lines.append(f"{title}:")

        if player.battlefield:
            for card in player.battlefield:
                card_text = self.format_card_details(card, show_full=True)
                lines.append(card_text)
        else:
            lines.append("  (empty)")

        return "\n".join(lines)

    def _format_stack(self, game_state: GameState) -> str:
        """Format the stack"""
        lines = []
        lines.append("STACK (top to bottom):")

        for spell in reversed(game_state.stack):
            spell_text = self.format_card_details(spell, show_full=True)
            lines.append(spell_text)

        return "\n".join(lines)

    def format_card_details(self, card: 'Card', show_full: bool = True) -> str:
        """Format complete card information"""
        lines = []

        # Name and mana cost
        mana_str = card.mana_cost.to_string()
        lines.append(f"{card.name} {mana_str}")

        if show_full:
            # Type line
            lines.append(f"  {card.type_line}")

            # Power/Toughness for creatures
            if card.is_creature():
                base_pt = f"{card.power}/{card.toughness}"
                current_pt = f"{card.current_power()}/{card.current_toughness()}"
                if base_pt != current_pt:
                    lines.append(f"  {base_pt} -> {current_pt}")
                else:
                    lines.append(f"  {current_pt}")

            # Oracle text
            if card.oracle_text:
                oracle_lines = card.oracle_text.split('\n')
                for oracle_line in oracle_lines:
                    lines.append(f"  {oracle_line}")

            # Current status
            status = self._get_card_status(card)
            if status:
                lines.append(f"  Status: {', '.join(status)}")

        return '\n'.join(lines)

    def _get_card_status(self, card: 'Card') -> List[str]:
        """Get status indicators for a card"""
        status = []

        # Counters
        if card.counters:
            for counter_type, amount in card.counters.items():
                status.append(f"{amount} {counter_type} counter{'s' if amount != 1 else ''}")

        # Tap status
        if card.is_tapped:
            status.append("tapped")

        # Summoning sickness
        if card.summoning_sick and card.zone == Zone.BATTLEFIELD:
            status.append("summoning sick")

        # Combat status
        if card.is_attacking:
            status.append("attacking")
        if card.is_blocking:
            status.append("blocking")

        return status

    def _get_opponent(self, game_state: GameState, player: Player) -> Player:
        """Get the opponent of the given player"""
        for p in game_state.players:
            if p != player:
                return p
        return None

    def format_actions(self, actions: List['Action']) -> str:
        """Format available actions for display"""
        if not actions:
            return "No actions available."

        lines = []
        lines.append("Available actions:")
        for i, action in enumerate(actions):
            lines.append(f"{i + 1}. {action.description}")

        return "\n".join(lines)

    def format_compact_card(self, card: 'Card') -> str:
        """Format card in compact form for lists"""
        mana_str = card.mana_cost.to_string()

        if card.is_creature():
            pt = f"({card.current_power()}/{card.current_toughness()})"
            return f"{card.name} {mana_str} {pt}"
        else:
            return f"{card.name} {mana_str}"


class GameLogger:
    """Logs game events and actions for replay/analysis"""

    def __init__(self):
        self.log_entries = []
        self.turn_number = 0

    def log_action(self, player_name: str, action_description: str):
        """Log a player action"""
        entry = f"Turn {self.turn_number}: {player_name} - {action_description}"
        self.log_entries.append(entry)

    def log_event(self, event_description: str):
        """Log a game event"""
        entry = f"Turn {self.turn_number}: {event_description}"
        self.log_entries.append(entry)

    def new_turn(self, turn_number: int):
        """Start logging a new turn"""
        self.turn_number = turn_number
        self.log_entries.append(f"\n--- TURN {turn_number} ---")

    def get_full_log(self) -> str:
        """Get the complete game log"""
        return "\n".join(self.log_entries)

    def get_recent_log(self, num_entries: int = 10) -> str:
        """Get recent log entries"""
        recent = self.log_entries[-num_entries:] if len(self.log_entries) > num_entries else self.log_entries
        return "\n".join(recent)


# Singleton formatters
game_formatter = GameStateFormatter()
game_logger = GameLogger()
