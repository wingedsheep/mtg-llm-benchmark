"""
Core prompting system for the MTG engine.
Provides a clean interface for requesting decisions from agents.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Any, Dict, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from engine.core.game_state import GameState
    from engine.core.player_system import Player


class PromptType(Enum):
    """Types of prompts that can be requested"""
    TARGET = "target"  # Select one or more targets by ID
    CHOICE = "choice"  # Choose from a list of options
    MULTI_CHOICE = "multi_choice"  # Choose multiple from a list of options
    TEXT = "text"  # Free text response
    YESNO = "yesno"  # Yes/No question
    CARD_CHOICE = "card_choice"  # Choose cards by ID
    NUMBER = "number"  # Choose a number within range


@dataclass
class PromptOption:
    """Represents an option in a prompt"""
    id: str
    display_text: str
    data: Dict[str, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


@dataclass
class PromptRequest:
    """Represents a request for agent input"""
    prompt_type: PromptType
    title: str
    description: str
    options: List[PromptOption] = None
    min_choices: int = 1
    max_choices: int = 1
    default_response: Any = None
    context_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.options is None:
            self.options = []
        if self.context_data is None:
            self.context_data = {}


@dataclass
class PromptResponse:
    """Represents an agent's response to a prompt"""
    selected_ids: List[str] = None
    text_response: str = None
    number_response: int = None
    boolean_response: bool = None

    def __post_init__(self):
        if self.selected_ids is None:
            self.selected_ids = []

    def get_single_id(self) -> Optional[str]:
        """Get the first selected ID, if any"""
        return self.selected_ids[0] if self.selected_ids else None

    def has_selections(self) -> bool:
        """Check if any IDs were selected"""
        return bool(self.selected_ids)


class PromptError(Exception):
    """Raised when prompting fails"""
    pass


class PromptManager:
    """Manages prompting flow between game engine and agents"""

    def __init__(self):
        self.prompt_callbacks: Dict[str, Callable] = {}

    def register_prompt_callback(self, player_name: str, callback: Callable):
        """Register a prompt callback for a player"""
        self.prompt_callbacks[player_name] = callback

    def request_prompt(self, game_state: 'GameState', player: 'Player',
                       prompt_request: PromptRequest) -> PromptResponse:
        """
        Request input from an agent

        Args:
            game_state: Current game state
            player: Player being prompted
            prompt_request: The prompt to send

        Returns:
            PromptResponse from the agent

        Raises:
            PromptError: If prompting fails or response is invalid
        """
        callback = self.prompt_callbacks.get(player.name)

        if not callback:
            # No callback registered - use default response
            if prompt_request.default_response is not None:
                return self._create_default_response(prompt_request)
            else:
                raise PromptError(f"No prompt callback registered for {player.name} and no default response")

        try:
            response = callback(game_state, player, prompt_request)
            self._validate_response(prompt_request, response)
            return response
        except Exception as e:
            if prompt_request.default_response is not None:
                return self._create_default_response(prompt_request)
            else:
                raise PromptError(f"Prompting failed for {player.name}: {e}")

    def _create_default_response(self, prompt_request: PromptRequest) -> PromptResponse:
        """Create a default response based on prompt type"""
        if prompt_request.prompt_type == PromptType.YESNO:
            return PromptResponse(boolean_response=bool(prompt_request.default_response))
        elif prompt_request.prompt_type == PromptType.NUMBER:
            return PromptResponse(number_response=int(prompt_request.default_response))
        elif prompt_request.prompt_type == PromptType.TEXT:
            return PromptResponse(text_response=str(prompt_request.default_response))
        elif prompt_request.prompt_type in [PromptType.TARGET, PromptType.CHOICE, PromptType.CARD_CHOICE]:
            if isinstance(prompt_request.default_response, list):
                return PromptResponse(selected_ids=prompt_request.default_response)
            else:
                return PromptResponse(selected_ids=[str(prompt_request.default_response)])
        elif prompt_request.prompt_type == PromptType.MULTI_CHOICE:
            return PromptResponse(selected_ids=prompt_request.default_response or [])
        else:
            return PromptResponse()

    def _validate_response(self, request: PromptRequest, response: PromptResponse):
        """Validate that response matches request requirements"""
        if request.prompt_type == PromptType.YESNO:
            if response.boolean_response is None:
                raise PromptError("Yes/No prompt requires boolean_response")

        elif request.prompt_type == PromptType.NUMBER:
            if response.number_response is None:
                raise PromptError("Number prompt requires number_response")

        elif request.prompt_type == PromptType.TEXT:
            if response.text_response is None:
                raise PromptError("Text prompt requires text_response")

        elif request.prompt_type in [PromptType.TARGET, PromptType.CHOICE, PromptType.CARD_CHOICE]:
            if not response.selected_ids:
                raise PromptError(f"{request.prompt_type.value} prompt requires selected_ids")
            if len(response.selected_ids) != 1:
                raise PromptError(f"{request.prompt_type.value} prompt requires exactly one selection")

        elif request.prompt_type == PromptType.MULTI_CHOICE:
            selections = len(response.selected_ids)
            if selections < request.min_choices:
                raise PromptError(f"Must select at least {request.min_choices} options")
            if selections > request.max_choices:
                raise PromptError(f"Must select at most {request.max_choices} options")

    def format_prompt_for_display(self, prompt_request: PromptRequest) -> str:
        """Format a prompt request for display to agents"""
        lines = []
        lines.append(f"=== {prompt_request.title.upper()} ===")
        lines.append(prompt_request.description)
        lines.append("")

        if prompt_request.prompt_type == PromptType.YESNO:
            lines.append("Respond with: 'yes' or 'no'")

        elif prompt_request.prompt_type == PromptType.TEXT:
            lines.append("Provide a text response.")

        elif prompt_request.prompt_type == PromptType.NUMBER:
            lines.append("Provide a number.")

        elif prompt_request.options:
            if prompt_request.prompt_type == PromptType.MULTI_CHOICE:
                lines.append(f"Choose {prompt_request.min_choices}-{prompt_request.max_choices} options by ID:")
            else:
                lines.append("Choose one option by ID:")

            for option in prompt_request.options:
                lines.append(f"  {option.id}: {option.display_text}")

        return "\n".join(lines)


# Singleton prompt manager
prompt_manager = PromptManager()
