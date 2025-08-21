"""
Enhanced sample game with improved phase logging and auto-skip functionality.
"""

import time

from gameplay.cards import Plains, Island, DockworkerDrone, BanishingLight, IllvoiGaleblade
from gameplay.engine.deck_system import DeckConfiguration
from gameplay.engine.game_setup import GameSetupManager
from gameplay.engine.game_state import GameState
from gameplay.example.simple_agent import SimpleAgent


def create_sample_deck_config() -> DeckConfiguration:
    """Create the specified deck configuration"""
    return DeckConfiguration([
        {'card_class': Plains, 'quantity': 10},
        {'card_class': Island, 'quantity': 7},
        {'card_class': DockworkerDrone, 'quantity': 9},
        {'card_class': BanishingLight, 'quantity': 6},
        {'card_class': IllvoiGaleblade, 'quantity': 8}
    ])


def run_enhanced_game(max_turns: int = 10, show_details: bool = True, delay: float = 0.3) -> str:
    """
    Run a game with enhanced logging and auto-skip functionality
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

    # Game loop
    turn_count = 0
    action_count = 0
    max_actions = 200  # Safety limit

    while not game.is_game_over() and turn_count < max_turns and action_count < max_actions:
        current_player = game.priority_player
        current_agent = agents[current_player.name]

        if show_details:
            print(f"\n>>> {game.get_current_phase_info()}")

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
        print(f"\n=== GAME LOG ===")
        print(game.get_game_log())

    return result


if __name__ == "__main__":
    # Run a single detailed game with enhanced logging
    print("Running enhanced game with auto-skip and detailed logging:")
    run_enhanced_game(max_turns=15, show_details=True, delay=0.5)
