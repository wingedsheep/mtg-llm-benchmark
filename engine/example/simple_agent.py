"""
Updated Simple AI agent for the MTG engine.
Now integrates with the prompt system for all decision making.
"""

from typing import List

from engine.core.actions_system import Action
from engine.core.mulligan_system import MulliganDecision
from engine.core.prompt_system import PromptRequest, PromptResponse, PromptType, prompt_manager
from engine.core.scry_system import ScryChoice


class SimpleAgent:
    """AI agent that makes strategic game decisions through the prompt system"""

    def __init__(self, name: str):
        self.name = name

    def register_with_game(self, game_state, player_name: str):
        """Register this agent's prompt callback with the game"""
        prompt_manager.register_prompt_callback(player_name, self.handle_prompt)

    def handle_prompt(self, game_state, player, prompt_request: PromptRequest) -> PromptResponse:
        """
        Handle any prompt request from the game engine

        Args:
            game_state: Current game state
            player: Player being prompted
            prompt_request: The prompt to respond to

        Returns:
            PromptResponse with the agent's decision
        """
        try:
            if prompt_request.prompt_type == PromptType.YESNO:
                return self._handle_yes_no_prompt(game_state, player, prompt_request)

            elif prompt_request.prompt_type == PromptType.TARGET:
                return self._handle_target_prompt(game_state, player, prompt_request)

            elif prompt_request.prompt_type in [PromptType.CHOICE, PromptType.CARD_CHOICE]:
                return self._handle_choice_prompt(game_state, player, prompt_request)

            elif prompt_request.prompt_type == PromptType.MULTI_CHOICE:
                return self._handle_multi_choice_prompt(game_state, player, prompt_request)

            elif prompt_request.prompt_type == PromptType.TEXT:
                return self._handle_text_prompt(game_state, player, prompt_request)

            elif prompt_request.prompt_type == PromptType.NUMBER:
                return self._handle_number_prompt(game_state, player, prompt_request)

            else:
                # Unknown prompt type - return default response
                return PromptResponse()

        except Exception as e:
            print(f"Error in SimpleAgent prompt handling: {e}")
            # Return default response on error
            return PromptResponse()

    def _handle_yes_no_prompt(self, game_state, player, prompt_request: PromptRequest) -> PromptResponse:
        """Handle yes/no prompts (mainly mulligan decisions)"""
        # Check if this is a mulligan decision
        if "Mulligan Decision" in prompt_request.title:
            return self._make_mulligan_decision(game_state, player, prompt_request)

        # For other yes/no prompts, use a simple heuristic
        # Generally be conservative (say no) unless there's clear benefit
        return PromptResponse(boolean_response=False)

    def _make_mulligan_decision(self, game_state, player, prompt_request: PromptRequest) -> PromptResponse:
        """Make mulligan decision using improved strategy"""
        context = prompt_request.context_data
        lands_count = context.get('lands_count', 0)
        spells_count = context.get('spells_count', 0)
        mulligan_count = context.get('mulligan_count', 0)

        # Stop mulliganing after 3 attempts
        if mulligan_count >= 3:
            return PromptResponse(boolean_response=True)  # Keep

        # Too few or too many lands
        if lands_count <= 1 or lands_count >= 5:
            return PromptResponse(boolean_response=False)  # Mulligan

        # Good land count (2-4), check if we have playable spells
        if 2 <= lands_count <= 4:
            # Keep if we have some spells we can cast
            affordable_spells = sum(1 for card in player.hand
                                  if not card.is_land() and card.mana_cost.total_cmc() <= lands_count + 1)
            if affordable_spells >= 1:
                return PromptResponse(boolean_response=True)  # Keep
            elif mulligan_count >= 1:  # Be less picky after first mulligan
                return PromptResponse(boolean_response=True)  # Keep

        return PromptResponse(boolean_response=False)  # Mulligan

    def _handle_target_prompt(self, game_state, player, prompt_request: PromptRequest) -> PromptResponse:
        """Handle target selection prompts"""
        if not prompt_request.options:
            return PromptResponse()

        # Simple strategy: prefer targeting opponent's most valuable permanent
        best_target = None
        best_score = -1

        for option in prompt_request.options:
            card = option.data.get('card')
            if not card:
                continue

            score = self._evaluate_target_value(card, player)
            if score > best_score:
                best_score = score
                best_target = option

        if best_target:
            return PromptResponse(selected_ids=[best_target.id])

        # Fallback: choose first option
        return PromptResponse(selected_ids=[prompt_request.options[0].id])

    def _evaluate_target_value(self, card, player) -> int:
        """Evaluate how valuable a card is as a target (higher = better target)"""
        score = 0

        # Prefer targeting opponent's cards over our own
        if card.controller != player:
            score += 10

        # Prefer creatures (they're threats)
        if card.is_creature():
            score += 5
            # Bigger creatures are better targets
            score += card.current_power() + card.current_toughness()

        # Prefer higher mana cost cards (more valuable)
        score += card.mana_cost.total_cmc()

        return score

    def _handle_choice_prompt(self, game_state, player, prompt_request: PromptRequest) -> PromptResponse:
        """Handle single choice prompts"""
        if not prompt_request.options:
            return PromptResponse()

        # For most choice prompts, evaluate each option and pick the best
        best_option = None
        best_score = -1

        for option in prompt_request.options:
            card = option.data.get('card')
            if card:
                score = self._evaluate_card_choice(card, player, prompt_request)
            else:
                # Non-card choice, use simple heuristic
                score = len(option.display_text)  # Prefer longer descriptions (more complex = better?)

            if score > best_score:
                best_score = score
                best_option = option

        if best_option:
            return PromptResponse(selected_ids=[best_option.id])

        # Fallback: first option
        return PromptResponse(selected_ids=[prompt_request.options[0].id])

    def _handle_multi_choice_prompt(self, game_state, player, prompt_request: PromptRequest) -> PromptResponse:
        """Handle multi-choice prompts (like cards to bottom, scry, etc.)"""
        if not prompt_request.options:
            return PromptResponse()

        # Check if this is a cards-to-bottom prompt
        if "Choose Cards to Bottom" in prompt_request.title:
            return self._handle_cards_to_bottom(game_state, player, prompt_request)

        # Check if this is a scry prompt
        if "Scry Decision" in prompt_request.title:
            return self._handle_scry_decision(game_state, player, prompt_request)

        # Generic multi-choice: pick the minimum required
        selected = []
        for i, option in enumerate(prompt_request.options[:prompt_request.min_choices]):
            selected.append(option.id)

        return PromptResponse(selected_ids=selected)

    def _handle_cards_to_bottom(self, game_state, player, prompt_request: PromptRequest) -> PromptResponse:
        """Handle choosing cards to put on bottom of library"""
        # Score each card - lower score = more likely to bottom
        scored_cards = []
        lands_in_hand = sum(1 for option in prompt_request.options
                           if option.data.get('card') and option.data['card'].is_land())

        for option in prompt_request.options:
            card = option.data.get('card')
            if not card:
                continue

            score = 0

            if card.is_land():
                # Keep lands if we don't have many
                if lands_in_hand <= 3:
                    score += 20
                else:
                    score += 5  # Still somewhat valuable
            else:
                # For spells, prefer cheaper ones
                cmc = card.mana_cost.total_cmc()
                score += max(0, 15 - cmc * 3)  # Cheaper = higher score

                # Bonus for creatures
                if card.is_creature():
                    score += 5

            scored_cards.append((score, option))

        # Sort by score (lowest first - these get bottomed)
        scored_cards.sort(key=lambda x: x[0])

        # Select the required number of lowest-scored cards
        selected_ids = []
        for i in range(min(prompt_request.min_choices, len(scored_cards))):
            selected_ids.append(scored_cards[i][1].id)

        return PromptResponse(selected_ids=selected_ids)

    def _handle_scry_decision(self, game_state, player, prompt_request: PromptRequest) -> PromptResponse:
        """Handle scry decisions"""
        # Simplified scry strategy: bottom lands if we have enough, expensive spells if we need cheaper ones
        lands_in_hand = sum(1 for card in player.hand if card.is_land())
        cards_to_bottom = []

        for option in prompt_request.options:
            card = option.data.get('card')
            if not card:
                continue

            # Bottom excess lands if we have enough
            if card.is_land() and lands_in_hand >= 3:
                cards_to_bottom.append(option.id)
                continue

            # Bottom very expensive spells if we don't have enough lands
            if not card.is_land() and lands_in_hand <= 2 and card.mana_cost.total_cmc() >= 5:
                cards_to_bottom.append(option.id)

        # Don't bottom more than half the cards
        max_to_bottom = len(prompt_request.options) // 2
        if len(cards_to_bottom) > max_to_bottom:
            cards_to_bottom = cards_to_bottom[:max_to_bottom]

        return PromptResponse(selected_ids=cards_to_bottom)

    def _handle_text_prompt(self, game_state, player, prompt_request: PromptRequest) -> PromptResponse:
        """Handle free text prompts"""
        # For creature type choices
        if "creature type" in prompt_request.description.lower():
            return PromptResponse(text_response="Human")

        # For color choices in text format
        if "color" in prompt_request.description.lower():
            return PromptResponse(text_response="White")

        # Default text response
        return PromptResponse(text_response="Default")

    def _handle_number_prompt(self, game_state, player, prompt_request: PromptRequest) -> PromptResponse:
        """Handle number choice prompts"""
        min_num = prompt_request.context_data.get('min_num', 0)
        max_num = prompt_request.context_data.get('max_num', 10)

        # Generally choose a moderate number
        chosen = (min_num + max_num) // 2

        return PromptResponse(number_response=chosen)

    def _evaluate_card_choice(self, card, player, prompt_request: PromptRequest) -> int:
        """Evaluate how good a card choice is"""
        score = 0

        # Prefer creatures for most choices
        if card.is_creature():
            score += 10
            score += card.current_power() + card.current_toughness()

        # Prefer lower mana cost for things we want to play
        cmc = card.mana_cost.total_cmc()
        score += max(0, 10 - cmc)

        return score

    # Legacy methods for backwards compatibility
    def make_mulligan_decision(self, player, mulligan_system) -> MulliganDecision:
        """DEPRECATED: Use prompt system instead"""
        info = mulligan_system.get_mulligan_info(player)
        lands = info['lands_in_hand']
        mulligan_count = info['mulligan_count']

        # Simple legacy logic
        if mulligan_count >= 3:
            return MulliganDecision("keep")
        if lands <= 1 or lands >= 5:
            return MulliganDecision("mulligan")
        if 2 <= lands <= 4:
            return MulliganDecision("keep")
        return MulliganDecision("mulligan")

    def choose_action(self, player, legal_actions: List[Action]) -> Action:
        """Choose action using existing logic"""
        if not legal_actions:
            return None

        # Existing action selection logic (unchanged)
        attack_actions = [a for a in legal_actions if a.action_type == "declare_attacks"]
        cast_spell_actions = [a for a in legal_actions if a.action_type == "cast_spell"]
        play_land_actions = [a for a in legal_actions if a.action_type == "play_land"]
        activate_ability_actions = [a for a in legal_actions if a.action_type == "activate_ability"]
        pass_actions = [a for a in legal_actions if a.action_type == "pass"]

        # 1. Always attack when we have creatures that can attack
        if attack_actions:
            best_attack = None
            max_attackers = -1

            for attack_action in attack_actions:
                attackers = attack_action.data.get('attackers', [])
                if len(attackers) > max_attackers:
                    max_attackers = len(attackers)
                    best_attack = attack_action

            if best_attack and max_attackers > 0:
                return best_attack
            elif attack_actions:
                return attack_actions[0]

        # 2. Play lands (always good)
        if play_land_actions:
            return play_land_actions[0]

        # 3. Cast creatures first (board presence is important)
        creature_spells = [a for a in cast_spell_actions
                          if a.data.get('card') and a.data['card'].is_creature()]
        if creature_spells:
            return self._choose_best_spell(creature_spells)

        # 4. Cast other spells
        if cast_spell_actions:
            return self._choose_best_spell(cast_spell_actions)

        # 5. Use beneficial activated abilities
        mana_abilities = [a for a in activate_ability_actions
                         if "Add" in a.description]
        if mana_abilities:
            return mana_abilities[0]

        # 6. Pass priority
        if pass_actions:
            return pass_actions[0]

        # Fallback
        return legal_actions[0] if legal_actions else None

    def _choose_best_spell(self, spell_actions: List[Action]) -> Action:
        """Choose the best spell to cast based on strategy"""
        if not spell_actions:
            return None

        scored_spells = []

        for action in spell_actions:
            card = action.data.get('card')
            if not card:
                continue

            score = 0
            cmc = card.mana_cost.total_cmc()

            # Prefer lower CMC spells
            score += max(0, 10 - cmc)

            # Bonus for creatures
            if card.is_creature():
                score += 5
                if card.power and card.toughness:
                    score += card.power + card.toughness

            scored_spells.append((score, action))

        # Sort by score (highest first)
        scored_spells.sort(key=lambda x: x[0], reverse=True)

        return scored_spells[0][1]

    # Additional legacy methods for backwards compatibility
    def make_scry_decision(self, player, scry_cards: List) -> ScryChoice:
        """DEPRECATED: Use prompt system instead"""
        return ScryChoice(cards_to_bottom=[], cards_to_top=scry_cards)

    def choose_cards_to_bottom(self, player, num_to_bottom: int) -> List[str]:
        """DEPRECATED: Use prompt system instead"""
        if num_to_bottom >= len(player.hand):
            return [card.id for card in player.hand]

        # Simple logic: bottom highest CMC cards
        sorted_cards = sorted(player.hand, key=lambda c: c.mana_cost.total_cmc(), reverse=True)
        return [card.id for card in sorted_cards[:num_to_bottom]]

    def __str__(self):
        return f"SimpleAgent({self.name})"
