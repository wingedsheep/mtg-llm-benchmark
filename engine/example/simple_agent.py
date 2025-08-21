"""
Improved Simple AI agent for the MTG engine.
Implements better decision-making strategies for game play.
"""

from typing import List

from engine.core.actions_system import Action
from engine.core.mulligan_system import MulliganDecision
from engine.core.scry_system import ScryChoice


class SimpleAgent:
    """Improved AI agent that makes strategic game decisions"""

    def __init__(self, name: str):
        self.name = name

    def make_mulligan_decision(self, player, mulligan_system) -> MulliganDecision:
        """
        Improved mulligan strategy:
        - Keep if 2-4 lands
        - Stop mulliganing after 3 attempts
        - Consider spell quality
        """
        info = mulligan_system.get_mulligan_info(player)
        lands = info['lands_in_hand']
        spells = info['spells_in_hand']
        mulligan_count = info['mulligan_count']

        # Stop mulliganing after 3 attempts
        if mulligan_count >= 3:
            return MulliganDecision("keep")

        # Too few or too many lands
        if lands <= 1 or lands >= 6:
            return MulliganDecision("mulligan")

        # Good land count (2-5), check if we have playable spells
        if 2 <= lands <= 5:
            # Keep if we have some spells we can cast
            affordable_spells = sum(1 for card in player.hand
                                   if not card.is_land() and card.mana_cost.total_cmc() <= lands + 1)
            if affordable_spells >= 1:
                return MulliganDecision("keep")
            elif mulligan_count >= 1:  # Be less picky after first mulligan
                return MulliganDecision("keep")

        return MulliganDecision("mulligan")

    def make_scry_decision(self, player, scry_cards: List) -> ScryChoice:
        """
        Improved scry strategy:
        - Bottom lands if we have enough
        - Bottom expensive spells if we need cheaper ones
        - Keep lands if we need them
        """
        lands_in_hand = sum(1 for card in player.hand if card.is_land())
        lands_in_scry = [card for card in scry_cards if card.is_land()]
        spells_in_scry = [card for card in scry_cards if not card.is_land()]

        cards_to_bottom = []

        # If we have enough lands, bottom excess lands from scry
        if lands_in_hand >= 3 and lands_in_scry:
            cards_to_bottom.extend(lands_in_scry[:max(1, len(lands_in_scry) // 2)])

        # Bottom very expensive spells if we don't have enough lands
        if lands_in_hand <= 2:
            expensive_spells = [card for card in spells_in_scry if card.mana_cost.total_cmc() >= 5]
            cards_to_bottom.extend(expensive_spells)

        # Keep the rest on top in original order
        cards_to_top = [card for card in scry_cards if card not in cards_to_bottom]

        return ScryChoice(cards_to_bottom=cards_to_bottom, cards_to_top=cards_to_top)

    def choose_action(self, player, legal_actions: List[Action]) -> Action:
        """
        Improved action selection strategy:
        1. Play lands when available
        2. Cast creatures before other spells
        3. Always attack when possible
        4. Use activated abilities when beneficial
        5. Pass when no good options
        """
        if not legal_actions:
            return None

        # Separate actions by type
        attack_actions = [a for a in legal_actions if a.action_type == "declare_attacks"]
        cast_spell_actions = [a for a in legal_actions if a.action_type == "cast_spell"]
        play_land_actions = [a for a in legal_actions if a.action_type == "play_land"]
        activate_ability_actions = [a for a in legal_actions if a.action_type == "activate_ability"]
        pass_actions = [a for a in legal_actions if a.action_type == "pass"]

        # 1. Always attack when we have creatures that can attack
        if attack_actions:
            # Find the attack action with the most attackers
            best_attack = None
            max_attackers = -1

            for attack_action in attack_actions:
                attackers = attack_action.data.get('attackers', [])
                if len(attackers) > max_attackers:
                    max_attackers = len(attackers)
                    best_attack = attack_action

            if best_attack and max_attackers > 0:
                return best_attack
            # If no good attacks, still need to declare (even with 0 attackers)
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
        """
        Choose the best spell to cast based on strategy
        """
        if not spell_actions:
            return None

        # Prioritize cheaper spells generally, but prefer creatures
        scored_spells = []

        for action in spell_actions:
            card = action.data.get('card')
            if not card:
                continue

            score = 0
            cmc = card.mana_cost.total_cmc()

            # Prefer lower CMC spells (we can cast them sooner)
            score += max(0, 10 - cmc)

            # Bonus for creatures (board presence)
            if card.is_creature():
                score += 5
                # Bonus for bigger creatures
                if card.power and card.toughness:
                    score += card.power + card.toughness

            scored_spells.append((score, action))

        # Sort by score (highest first)
        scored_spells.sort(key=lambda x: x[0], reverse=True)

        return scored_spells[0][1]

    def choose_cards_to_bottom(self, player, num_to_bottom: int) -> List:
        """
        Choose which cards to put on bottom of library during mulligan
        Strategy: Bottom the most expensive cards that we can't cast soon
        """
        if num_to_bottom >= len(player.hand):
            return player.hand.copy()

        # Score each card - lower score = more likely to bottom
        scored_cards = []
        lands_in_hand = sum(1 for card in player.hand if card.is_land())

        for card in player.hand:
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

            scored_cards.append((score, card))

        # Sort by score (lowest first - these get bottomed)
        scored_cards.sort(key=lambda x: x[0])

        return [card for score, card in scored_cards[:num_to_bottom]]

    def __str__(self):
        return f"SimpleAgent({self.name})"
