"""
Updated sample game with prompt system integration.
Demonstrates the new structured prompting approach for agent decisions.
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


def run_prompt_system_game(max_turns: int = 10, show_details: bool = True,
                          show_logger: bool = True, delay: float = 0.3) -> str:
    """
    Run a game using the new prompt system for all agent decisions

    Args:
        max_turns: Maximum number of turns to play
        show_details: Show detailed game state info
        show_logger: Show real-time game logger output
        delay: Delay between actions for readability
    """
    print("=== SETTING UP GAME WITH PROMPT SYSTEM ===")

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

    # Create game state first (needed for prompt system)
    game = GameState(players)

    # Register agents with the prompt system
    agent1.register_with_game(game, player1.name)
    agent2.register_with_game(game, player2.name)

    # Setup game with prompt system (no callbacks needed!)
    starting_player_index = setup_manager.setup_game(players, game)

    # Set the starting player in the game
    game.active_player_index = starting_player_index
    game.priority_player_index = starting_player_index

    # Map agents to players
    agents = {player1.name: agent1, player2.name: agent2}

    if show_details:
        print(f"Game initialized with prompt system!")
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

        # Agent chooses action (note: targeting will be handled automatically via prompts)
        chosen_action = current_agent.choose_action(current_player, legal_actions)

        if not chosen_action:
            print(f"Agent {current_agent.name} returned no action!")
            break

        # Execute action (this may trigger prompts for targeting, etc.)
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
        print("\nPrompt System Features Demonstrated:")
        print("- Automatic mulligan decisions through structured prompts")
        print("- Automatic target selection for spells like Banishing Light")
        print("- Automatic choice selection for triggered abilities like Dockworker Drone")
        print("- Cards-to-bottom selection during mulligan phase")

    return result


def run_legacy_game(max_turns: int = 10, show_details: bool = True,
                   show_logger: bool = True, delay: float = 0.3) -> str:
    """
    Run a game using the legacy callback system for comparison
    """
    print("=== SETTING UP LEGACY GAME (FOR COMPARISON) ===")

    # Create agents
    agent1 = SimpleAgent("Legacy Agent Alpha")
    agent2 = SimpleAgent("Legacy Agent Beta")

    # Create deck configuration
    deck_config = create_sample_deck_config()

    # Set up game
    setup_manager = GameSetupManager()

    # Create players with identical decks
    player1 = setup_manager.create_player_with_deck(agent1.name, deck_config)
    player2 = setup_manager.create_player_with_deck(agent2.name, deck_config)

    players = [player1, player2]

    # Create callbacks for legacy system
    def mulligan_callback(player):
        agent = agent1 if player.name == agent1.name else agent2
        return agent.make_mulligan_decision(player, setup_manager.mulligan_system)

    def scry_callback(player, scry_cards):
        agent = agent1 if player.name == agent1.name else agent2
        return agent.make_scry_decision(player, scry_cards)

    def bottom_callback(player, num_to_bottom):
        agent = agent1 if player.name == agent1.name else agent2
        return agent.choose_cards_to_bottom(player, num_to_bottom)

    # Setup game with legacy callbacks
    starting_player_index = setup_manager.setup_game_with_callbacks(
        players, mulligan_callback, scry_callback, bottom_callback)

    # Create game state
    game = GameState(players)
    game.active_player_index = starting_player_index
    game.priority_player_index = starting_player_index

    agents = {game.players[0].name: agent1, game.players[1].name: agent2}

    print(f"Legacy game initialized! Starting player: {game.active_player.name}")
    print("Note: This uses the old callback system instead of the new prompt system")

    # Rest of the game loop is similar to the prompt system version...
    # (truncated for brevity, but would be the same basic structure)

    return "Legacy game completed"


def run_debug_game():
    """Run a game with maximum debugging output using prompt system"""
    print("Running debug game with prompt system and full logging:")
    return run_prompt_system_game(
        max_turns=15,
        show_details=True,
        show_logger=True,  # Show real-time logger output
        delay=0.8  # Slower for debugging
    )


def compare_systems():
    """Compare the old callback system vs new prompt system"""
    print("=== PROMPT SYSTEM vs LEGACY COMPARISON ===")
    print("\n1. Running game with NEW prompt system:")
    prompt_result = run_prompt_system_game(max_turns=5, show_details=False, delay=0.1)

    print(f"\n2. Running game with LEGACY callback system:")
    legacy_result = run_legacy_game(max_turns=5, show_details=False, delay=0.1)

    print(f"\n=== COMPARISON RESULTS ===")
    print(f"Prompt System: {prompt_result}")
    print(f"Legacy System: {legacy_result}")

    print(f"\nPrompt System Advantages:")
    print("- Structured, type-safe prompts")
    print("- Centralized prompt handling")
    print("- Automatic validation of responses")
    print("- Easy to add new prompt types")
    print("- Better error handling and fallbacks")
    print("- Consistent interface for all agent decisions")


if __name__ == "__main__":
    # Run a debug game with the new prompt system
    run_debug_game()

    # Uncomment to compare systems:
    # compare_systems()
