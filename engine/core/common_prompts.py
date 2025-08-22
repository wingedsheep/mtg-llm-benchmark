"""
Common prompt types used throughout the MTG engine.
Provides factory functions for frequently used prompts.
"""

from typing import List, TYPE_CHECKING

from engine.core.prompt_system import PromptRequest, PromptResponse, PromptOption, PromptType

if TYPE_CHECKING:
    from engine.core.player_system import Player
    from engine.core.card_system import Card


class CommonPrompts:
    """Factory class for common prompt types"""

    @staticmethod
    def create_target_prompt(title: str, description: str, valid_targets: List['Card']) -> PromptRequest:
        """Create a prompt for selecting a single target"""
        options = []
        for target in valid_targets:
            display = target.get_display_info_for_targeting()
            options.append(PromptOption(
                id=target.id,
                display_text=display,
                data={"card": target}
            ))

        return PromptRequest(
            prompt_type=PromptType.TARGET,
            title=title,
            description=description,
            options=options
        )

    @staticmethod
    def create_card_choice_prompt(title: str, description: str, cards: List['Card'],
                                  min_choices: int = 1, max_choices: int = 1) -> PromptRequest:
        """Create a prompt for choosing cards from a list"""
        options = []
        for card in cards:
            mana_str = card.mana_cost.to_string()
            display_text = f"{card.name} {mana_str}"
            if card.is_creature():
                display_text += f" ({card.current_power()}/{card.current_toughness()})"

            options.append(PromptOption(
                id=card.id,
                display_text=display_text,
                data={"card": card}
            ))

        prompt_type = PromptType.MULTI_CHOICE if max_choices > 1 else PromptType.CARD_CHOICE

        return PromptRequest(
            prompt_type=prompt_type,
            title=title,
            description=description,
            options=options,
            min_choices=min_choices,
            max_choices=max_choices
        )

    @staticmethod
    def create_mulligan_prompt(player: 'Player', mulligan_count: int,
                               lands_in_hand: int, spells_in_hand: int) -> PromptRequest:
        """Create a mulligan decision prompt"""
        description = (
            f"Hand: {len(player.hand)} cards ({lands_in_hand} lands, {spells_in_hand} spells)\n"
            f"Mulligan count: {mulligan_count}\n\n"
            f"Current hand:\n"
        )

        for i, card in enumerate(player.hand):
            mana_str = card.mana_cost.to_string()
            card_display = f"{card.name} {mana_str}"
            if card.is_creature():
                card_display += f" ({card.current_power()}/{card.current_toughness()})"
            description += f"  {i + 1}. {card_display}\n"

        description += "\nDo you want to keep this hand or mulligan?"

        return PromptRequest(
            prompt_type=PromptType.YESNO,
            title="Mulligan Decision",
            description=description,
            context_data={
                "mulligan_count": mulligan_count,
                "hand_size": len(player.hand),
                "lands_count": lands_in_hand,
                "spells_count": spells_in_hand
            },
            default_response=True  # Default to keeping
        )

    @staticmethod
    def create_cards_to_bottom_prompt(player: 'Player', num_to_bottom: int) -> PromptRequest:
        """Create a prompt for choosing cards to put on bottom of library"""
        description = (
            f"Choose {num_to_bottom} cards from your hand to put on the bottom of your library "
            f"(in any order).\n\nYour hand:\n"
        )

        cards = player.hand.copy()
        options = []
        for card in cards:
            mana_str = card.mana_cost.to_string()
            display_text = f"{card.name} {mana_str}"
            if card.is_creature():
                display_text += f" ({card.current_power()}/{card.current_toughness()})"

            options.append(PromptOption(
                id=card.id,
                display_text=display_text,
                data={"card": card}
            ))

        return PromptRequest(
            prompt_type=PromptType.MULTI_CHOICE,
            title="Choose Cards to Bottom",
            description=description,
            options=options,
            min_choices=num_to_bottom,
            max_choices=num_to_bottom
        )

    @staticmethod
    def create_creature_type_prompt(context: str) -> PromptRequest:
        """Create a prompt for choosing a creature type"""
        description = f"{context}\n\nChoose a creature type (e.g., 'Human', 'Goblin', 'Dragon', etc.)"

        return PromptRequest(
            prompt_type=PromptType.TEXT,
            title="Choose Creature Type",
            description=description,
            default_response="Human"
        )

    @staticmethod
    def create_color_choice_prompt(context: str, available_colors: List[str] = None) -> PromptRequest:
        """Create a prompt for choosing a color"""
        if available_colors is None:
            available_colors = ["White", "Blue", "Black", "Red", "Green"]

        options = []
        for color in available_colors:
            options.append(PromptOption(
                id=color.lower(),
                display_text=color
            ))

        return PromptRequest(
            prompt_type=PromptType.CHOICE,
            title="Choose Color",
            description=context,
            options=options,
            default_response=available_colors[0].lower() if available_colors else "white"
        )

    @staticmethod
    def create_number_choice_prompt(context: str, min_num: int = 0, max_num: int = 10) -> PromptRequest:
        """Create a prompt for choosing a number"""
        description = f"{context}\n\nChoose a number between {min_num} and {max_num}."

        return PromptRequest(
            prompt_type=PromptType.NUMBER,
            title="Choose Number",
            description=description,
            context_data={"min_num": min_num, "max_num": max_num},
            default_response=min_num
        )

    @staticmethod
    def create_scry_prompt(player: 'Player', scry_cards: List['Card']) -> PromptRequest:
        """Create a prompt for scry decisions"""
        description = f"Scrying {len(scry_cards)} cards. Choose which cards to put on the bottom of your library.\n\n"
        description += "Cards being scried:\n"

        for i, card in enumerate(scry_cards):
            mana_str = card.mana_cost.to_string()
            card_display = f"{card.name} {mana_str}"
            if card.is_creature():
                card_display += f" ({card.current_power()}/{card.current_toughness()})"
            description += f"  {i + 1}. {card_display}\n"

        description += "\nCards not chosen will be put back on top in the same order."

        options = []
        for card in scry_cards:
            mana_str = card.mana_cost.to_string()
            display_text = f"{card.name} {mana_str}"
            if card.is_creature():
                display_text += f" ({card.current_power()}/{card.current_toughness()})"

            options.append(PromptOption(
                id=card.id,
                display_text=display_text,
                data={"card": card}
            ))

        return PromptRequest(
            prompt_type=PromptType.MULTI_CHOICE,
            title="Scry Decision",
            description=description,
            options=options,
            min_choices=0,
            max_choices=len(scry_cards),
            default_response=[]  # Default to keeping all on top
        )

    @staticmethod
    def create_yes_no_prompt(title: str, question: str, default: bool = False) -> PromptRequest:
        """Create a simple yes/no prompt"""
        return PromptRequest(
            prompt_type=PromptType.YESNO,
            title=title,
            description=question,
            default_response=default
        )


class PromptResponseHelper:
    """Helper functions for processing prompt responses"""

    @staticmethod
    def get_selected_cards(response: PromptResponse, all_cards: List['Card']) -> List['Card']:
        """Get the actual card objects from selected IDs"""
        if not response.selected_ids:
            return []

        selected_cards = []
        card_map = {card.id: card for card in all_cards}

        for card_id in response.selected_ids:
            if card_id in card_map:
                selected_cards.append(card_map[card_id])

        return selected_cards

    @staticmethod
    def is_yes_response(response: PromptResponse) -> bool:
        """Check if response is 'yes' for yes/no prompts"""
        return response.boolean_response is True

    @staticmethod
    def is_no_response(response: PromptResponse) -> bool:
        """Check if response is 'no' for yes/no prompts"""
        return response.boolean_response is False
