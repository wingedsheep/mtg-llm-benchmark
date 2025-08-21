"""
Enhanced sample game with improved phase logging and detailed game logger output.
"""

import time

from engine.cards import Plains, Island, DockworkerDrone, BanishingLight, IllvoiGaleblade
from engine.core.deck_system import DeckConfiguration
from engine.core.display_system import game_logger
from engine.core.game_setup import GameSetupManager
from engine.core.game_state import GameState
from engine.example.simple_agent import SimpleAgent


def create_sample_deck_config() -> DeckConfiguration:
    """Create the specified deck configuration"""
    return DeckConfiguration([
        {'card_class': Plains, 'quantity': 10},
        {'card_class': Island, 'quantity': 7},
        {'card_class': DockworkerDrone, 'quantity': 9},
        {'card_class': BanishingLight, 'quantity': 6},
        {'card_class': IllvoiGaleblade, 'quantity': 8}
    ])


def run_enhanced_game(max_turns: int = 10, show_details: bool = True,
                     show_logger: bool = True, delay: float = 0.3) -> str:
    """
    Run a game with enhanced logging and real-time game logger output

    Args:
        max_turns: Maximum number of turns to play
        show_details: Show detailed game state info
        show_logger: Show real-time game logger output
        delay: Delay between actions for readability
    """
    print("=== SETTING UP ENHANCED GAME ===")

    # Create agents
    agent1 = SimpleAgent("Agent Alpha")
    agent2 = SimpleAgent("Agent Beta")

    # Create deck configuration
    deck_config = create_sample_deck_config()

    # Set up game
    setup_manager = GameSetupManager()

    # Create players with identical decks
    player1 = setup_manager.create_player_with_deck(agent1.name, deck_config)
    player2 = setup_manager.create_player_with_deck(agent2.name, deck_config)

    players = [player1, player2]

    # Create callbacks
    def mulligan_callback(player):
        agent = agent1 if player.name == agent1.name else agent2
        return agent.make_mulligan_decision(player, setup_manager.mulligan_system)

    def scry_callback(player, scry_cards):
        agent = agent1 if player.name == agent1.name else agent2
        return agent.make_scry_decision(player, scry_cards)

    def bottom_callback(player, num_to_bottom):
        agent = agent1 if player.name == agent1.name else agent2
        return agent.choose_cards_to_bottom(player, num_to_bottom)

    # Setup game with mulligans
    starting_player_index = setup_manager.setup_game(players, mulligan_callback, scry_callback, bottom_callback)

    # Create game state
    game = GameState(players)
    game.active_player_index = starting_player_index
    game.priority_player_index = starting_player_index

    agents = {game.players[0].name: agent1, game.players[1].name: agent2}

    if show_details:
        print(f"Game initialized!")
        print(f"Starting player: {game.active_player.name}")
        print(f"Phase info: {game.get_current_phase_info()}")

    print(f"\n=== GAME START ===")

    # Track last logger position to show new entries
    last_log_position = 0

    # Game loop
    turn_count = 0
    action_count = 0
    max_actions = 200  # Safety limit

    while not game.is_game_over() and turn_count < max_turns and action_count < max_actions:
        current_player = game.priority_player
        current_agent = agents[current_player.name]

        if show_details:
            print(f"\n>>> {game.get_current_phase_info()}")

            # Show recent game state
            if action_count % 5 == 0:  # Show every 5 actions to avoid spam
                print(f"\n--- GAME STATE ---")
                print(f"{current_player.name}: {current_player.life} life, {len(current_player.hand)} cards in hand, {len(current_player.battlefield)} permanents")
                opponent = game.players[0] if game.players[1] == current_player else game.players[1]
                print(f"{opponent.name}: {opponent.life} life, {len(opponent.hand)} cards in hand, {len(opponent.battlefield)} permanents")

                if current_player.battlefield:
                    print(f"{current_player.name}'s battlefield:")
                    for permanent in current_player.battlefield:
                        status = " (tapped)" if permanent.is_tapped else ""
                        if permanent.is_creature():
                            print(f"  - {permanent.name} {permanent.current_power()}/{permanent.current_toughness()}{status}")
                        else:
                            print(f"  - {permanent.name}{status}")

        # Get legal actions
        legal_actions = game.get_legal_actions(current_player)

        if not legal_actions:
            # This should rarely happen due to auto-skip, but just in case
            print(f"No legal actions for {current_player.name} - passing")
            game.pass_priority()
            continue

        # Agent chooses action
        chosen_action = current_agent.choose_action(current_player, legal_actions)

        if not chosen_action:
            print(f"Agent {current_agent.name} returned no action!")
            break

        # Execute action
        success = game.execute_action(current_player, chosen_action)

        if not success:
            print(f"Failed to execute action: {chosen_action.description}")
            break

        # Show action if detailed
        if show_details:
            print(f"Action: {chosen_action.description}")

        # Show new game logger entries in real-time
        if show_logger:
            current_log = game_logger.get_full_log()
            if current_log:
                log_lines = current_log.split('\n')
                if len(log_lines) > last_log_position:
                    new_lines = log_lines[last_log_position:]
                    for line in new_lines:
                        if line.strip():  # Skip empty lines
                            print(f"  LOG: {line}")
                    last_log_position = len(log_lines)

        action_count += 1

        # Track turn changes
        if game.turn_number > turn_count:
            turn_count = game.turn_number
            if show_details:
                print(f"\n--- TURN {turn_count} SUMMARY ---")
                for player in game.players:
                    print(f"{player.name}: Life {player.life}, {len(player.hand)} cards, {len(player.battlefield)} permanents")

        # Small delay for readability
        if delay > 0:
            time.sleep(delay)

    # Game over
    print(f"\n=== GAME OVER ===")

    if game.is_game_over():
        winner = game.get_winner()
        if winner:
            result = f"{winner.name} wins!"
            print(result)
            if show_details:
                print(f"Final life totals:")
                for player in game.players:
                    print(f"  {player.name}: {player.life} life")
        else:
            result = "Game ended in a draw!"
            print(result)
    else:
        result = f"Game ended after {max_turns} turns or {max_actions} actions"
        print(result)

    if show_details:
        print(f"\nTotal actions taken: {action_count}")
        print(f"Turns played: {turn_count}")

    return result


def run_debug_game():
    """Run a game with maximum debugging output"""
    print("Running debug game with full logging:")
    return run_enhanced_game(
        max_turns=15,
        show_details=True,
        show_logger=True,  # Show real-time logger output
        delay=0.8  # Slower for debugging
    )

if __name__ == "__main__":
    # Run a debug game with full logging
    run_debug_game()
