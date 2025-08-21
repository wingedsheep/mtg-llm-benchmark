"""
Fixed actions system for the MTG engine.
Handles proper action generation based on game phase and player priority.
FIXED: Prevents getting stuck in attack declaration phase.
"""

from typing import List, Callable, Any, TYPE_CHECKING

from engine.core.core_types import Phase, CardType
from engine.core.display_system import game_logger

if TYPE_CHECKING:
    from engine.core.game_state import GameState
    from engine.core.player_system import Player
    from engine.core.card_system import Card


class Action:
    """Represents a possible game action"""

    def __init__(self, action_type: str, description: str,
                 execute_func: Callable[['GameState'], Any], **kwargs):
        self.action_type = action_type
        self.description = description
        self.execute_func = execute_func
        self.data = kwargs

    def execute(self, game_state: 'GameState') -> Any:
        """Execute this action"""
        return self.execute_func(game_state)

    def __str__(self) -> str:
        return self.description

    def __repr__(self) -> str:
        return f"Action({self.action_type}: {self.description})"


class ActionGenerator:
    """Generates legal actions for players based on game state"""

    def __init__(self):
        # Track whether attacks have been declared this combat
        self.attacks_declared_this_phase = False
        self.blocks_declared_this_phase = False

    def get_legal_actions(self, game_state: 'GameState', player: 'Player') -> List[Action]:
        """Get all legal actions for a player in the current game state"""
        actions = []

        # Always allow passing priority if player has priority
        if player == game_state.priority_player:
            actions.append(self._create_pass_action(game_state))

        # Phase-specific actions for active player
        if player == game_state.active_player:
            actions.extend(self._get_active_player_actions(game_state, player))

        # Phase-specific actions for non-active player
        if player != game_state.active_player:
            actions.extend(self._get_non_active_player_actions(game_state, player))

        # Instant-speed actions (available to player with priority)
        if player == game_state.priority_player:
            actions.extend(self._get_instant_speed_actions(game_state, player))

        return actions

    def reset_combat_flags(self):
        """Reset combat-related flags - called when entering a new combat phase"""
        self.attacks_declared_this_phase = False
        self.blocks_declared_this_phase = False

    def _create_pass_action(self, game_state: 'GameState') -> Action:
        """Create pass priority action"""

        def pass_priority(gs):
            gs.pass_priority()

        return Action("pass", "Pass priority", pass_priority)

    def _get_active_player_actions(self, game_state: 'GameState', player: 'Player') -> List[Action]:
        """Get actions available to the active player"""
        actions = []

        # Main phase actions
        if game_state.phase in [Phase.MAIN1, Phase.MAIN2]:
            actions.extend(self._get_main_phase_actions(game_state, player))

        # Combat phase actions
        elif game_state.phase == Phase.COMBAT_DECLARE_ATTACKERS:
            # Only allow attack declaration if not already declared
            if not self.attacks_declared_this_phase:
                actions.extend(self._get_attack_actions(game_state, player))

        return actions

    def _get_non_active_player_actions(self, game_state: 'GameState', player: 'Player') -> List[Action]:
        """Get actions available to the non-active player"""
        actions = []

        # Blocking actions
        if game_state.phase == Phase.COMBAT_DECLARE_BLOCKERS:
            # Only allow block declaration if not already declared
            if not self.blocks_declared_this_phase:
                actions.extend(self._get_block_actions(game_state, player))

        return actions

    def _get_main_phase_actions(self, game_state: 'GameState', player: 'Player') -> List[Action]:
        """Get actions available during main phases"""
        actions = []

        # Play lands (only if player has priority and is active player)
        if (player == game_state.priority_player and
            not player.has_played_land_this_turn):
            lands_in_hand = [card for card in player.hand if card.is_land()]
            for land in lands_in_hand:
                actions.append(self._create_play_land_action(game_state, player, land))

        # Cast sorcery-speed spells
        for spell in player.hand:
            if (spell.is_spell() and
                not spell.has_type(CardType.INSTANT) and
                player.can_cast_spell(spell)):
                actions.append(self._create_cast_spell_action(game_state, player, spell))

        return actions

    def _get_attack_actions(self, game_state: 'GameState', player: 'Player') -> List[Action]:
        """Get attack declaration actions"""
        actions = []

        # Get potential attackers
        potential_attackers = [c for c in player.get_creatures() if c.can_attack()]

        if potential_attackers:
            # Attack with all creatures
            actions.append(self._create_attack_action(game_state, player, potential_attackers))

            # Attack with individual creatures (for more tactical play)
            for attacker in potential_attackers:
                actions.append(self._create_attack_action(game_state, player, [attacker]))

        # Always allow attacking with no creatures (to progress the phase)
        actions.append(self._create_attack_action(game_state, player, []))

        return actions

    def _get_block_actions(self, game_state: 'GameState', player: 'Player') -> List[Action]:
        """Get blocking actions for defending player"""
        actions = []

        # For simplicity, just allow no blocks for now
        # TODO: Implement proper blocking choices
        actions.append(self._create_block_action(game_state, player, []))

        return actions

    def _get_instant_speed_actions(self, game_state: 'GameState', player: 'Player') -> List[Action]:
        """Get actions available at instant speed"""
        actions = []

        # Activated abilities
        for card in player.battlefield:
            for ability in card.get_activated_abilities():
                if ability.can_activate(card):
                    actions.append(self._create_activate_ability_action(game_state, player, card, ability))

        # Cast instant spells
        for spell in player.hand:
            if (spell.has_type(CardType.INSTANT) and
                    player.can_cast_spell(spell)):
                actions.append(self._create_cast_spell_action(game_state, player, spell))

        return actions

    def _create_play_land_action(self, game_state: 'GameState', player: 'Player', land: 'Card') -> Action:
        """Create a play land action"""

        def play_land(gs):
            success = player.play_land(land)
            if success:
                # Trigger ETB effects
                from engine.core.core_types import GameEvent
                etb_event = GameEvent("enters_battlefield", card=land)
                gs.trigger_manager.check_triggers(etb_event, gs)
                return True
            return False

        return Action("play_land", f"Play {land.name}", play_land, card=land)

    def _create_cast_spell_action(self, game_state: 'GameState', player: 'Player', spell: 'Card') -> Action:
        """Create a cast spell action"""

        def cast_spell(gs):
            success = player.cast_spell(spell)
            if success and spell.is_creature():
                # Trigger ETB effects for creatures
                from engine.core.core_types import GameEvent
                etb_event = GameEvent("enters_battlefield", card=spell)
                gs.trigger_manager.check_triggers(etb_event, gs)
                return True
            return success

        mana_str = spell.mana_cost.to_string()
        description = f"Cast {spell.name} {mana_str}"

        return Action("cast_spell", description, cast_spell, card=spell)

    def _create_activate_ability_action(self, game_state: 'GameState', player: 'Player',
                                        card: 'Card', ability) -> Action:
        """Create an activate ability action"""

        def activate_ability(gs):
            return ability.activate(gs, card)

        description = f"Activate {card.name}: {ability.effect.description}"
        return Action("activate_ability", description, activate_ability, card=card, ability=ability)

    def _create_attack_action(self, game_state: 'GameState', player: 'Player',
                              attackers: List['Card']) -> Action:
        """Create an attack action"""

        def declare_attacks(gs):
            # Mark that attacks have been declared this phase
            self.attacks_declared_this_phase = True

            # Clear existing attacks
            for creature in player.get_creatures():
                creature.is_attacking = False

            # Declare new attacks
            for attacker in attackers:
                if attacker.can_attack():
                    attacker.is_attacking = True
                    attacker.is_tapped = True

            # Log attack details
            if attackers:
                attacker_names = [a.name for a in attackers]
                game_logger.log_event(f"Attacking with: {', '.join(attacker_names)}")
            else:
                game_logger.log_event("No creatures declared as attackers")

            # Move to next phase will be handled by the phase system automatically
            # when all players pass priority
            return True

        if not attackers:
            description = "Declare no attackers"
        elif len(attackers) == 1:
            description = f"Attack with {attackers[0].name}"
        else:
            description = f"Attack with {len(attackers)} creatures"

        return Action("declare_attacks", description, declare_attacks, attackers=attackers)

    def _create_block_action(self, game_state: 'GameState', player: 'Player',
                             blockers: List['Card']) -> Action:
        """Create a block action"""

        def declare_blocks(gs):
            # Mark that blocks have been declared this phase
            self.blocks_declared_this_phase = True

            # Clear existing blocks
            for creature in player.get_creatures():
                creature.is_blocking = False

            # For now, simplified blocking
            if blockers:
                blocker_names = [b.name for b in blockers]
                game_logger.log_event(f"Blocking with: {', '.join(blocker_names)}")
            else:
                game_logger.log_event("No creatures declared as blockers")

            return True

        description = "Declare no blockers" if not blockers else f"Block with {len(blockers)} creatures"
        return Action("declare_blocks", description, declare_blocks, blockers=blockers)


class ActionValidator:
    """Validates whether actions are legal in the current game state"""

    @staticmethod
    def is_action_legal(action: Action, game_state: 'GameState', player: 'Player') -> bool:
        """Check if an action is legal for a player in the current state"""

        # Player must have priority to take any action
        if player != game_state.priority_player:
            return False

        if action.action_type == "pass":
            return True

        elif action.action_type == "play_land":
            return (player == game_state.active_player and
                    game_state.phase in [Phase.MAIN1, Phase.MAIN2] and
                    not player.has_played_land_this_turn and
                    action.data.get('card') in player.hand)

        elif action.action_type == "cast_spell":
            card = action.data.get('card')
            if not card or card not in player.hand:
                return False

            # Sorcery-speed spells only in main phases for active player
            if not card.has_type(CardType.INSTANT):
                return (player == game_state.active_player and
                        game_state.phase in [Phase.MAIN1, Phase.MAIN2])

            # Instants can be cast anytime with priority
            return player.can_cast_spell(card)

        elif action.action_type == "activate_ability":
            # Most abilities can be activated at instant speed
            card = action.data.get('card')
            ability = action.data.get('ability')
            return card and ability and ability.can_activate(card)

        elif action.action_type == "declare_attacks":
            # Can only declare attacks once per combat phase
            return (player == game_state.active_player and
                    game_state.phase == Phase.COMBAT_DECLARE_ATTACKERS and
                    not action_generator.attacks_declared_this_phase)

        elif action.action_type == "declare_blocks":
            # Can only declare blocks once per combat phase
            return (player != game_state.active_player and
                    game_state.phase == Phase.COMBAT_DECLARE_BLOCKERS and
                    not action_generator.blocks_declared_this_phase)

        return False


# Singleton action generator
action_generator = ActionGenerator()
action_validator = ActionValidator()
