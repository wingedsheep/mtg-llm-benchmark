"""
Card system for the MTG engine.
Contains the base Card class and card-related functionality.
"""

import uuid
from typing import List, Dict, Optional

from cards import Card

from engine.core.core_types import Zone, CardType
from engine.core.game_state import GameState
from engine.core.mana_system import ManaCost
from engine.core.player_system import Player
from engine.core.targeting_system import TargetFilter


class Card:
    """Base card class that can be programmatically defined"""

    def __init__(self, name: str, mana_cost: str, type_line: str,
                 oracle_text: str, colors: List[str], power: str = None,
                 toughness: str = None, rarity: str = "common"):
        # Card definition
        self.name = name
        self.mana_cost = ManaCost.from_string(mana_cost)
        self.type_line = type_line
        self.oracle_text = oracle_text
        self.colors = colors
        self.power = int(power) if power else None
        self.toughness = int(toughness) if toughness else None
        self.rarity = rarity

        # Game state
        self.zone = Zone.LIBRARY
        self.owner: Optional[Player] = None
        self.controller: Optional[Player] = None
        self.id = str(uuid.uuid4())  # Unique identifier

        # Permanent state
        self.counters: Dict[str, int] = {}
        self.is_tapped = False
        self.is_attacking = False
        self.is_blocking = False
        self.summoning_sick = True

        # Effects and abilities - avoid circular imports
        self.abilities: List = []
        self.static_effects: List = []

        # Parse card types
        self.card_types = self._parse_types()

        # Initialize card-specific behavior
        self.setup_card_behavior()

    def _parse_types(self) -> List[CardType]:
        """Parse type line into card types"""
        types = []
        type_line_lower = self.type_line.lower()
        for card_type in CardType:
            if card_type.value in type_line_lower:
                types.append(card_type)
        return types

    def setup_card_behavior(self):
        """Override this method to define card-specific behavior"""
        pass

    def add_counter(self, counter_type: str, amount: int = 1):
        """Add counters to this card"""
        self.counters[counter_type] = self.counters.get(counter_type, 0) + amount

    def remove_counter(self, counter_type: str, amount: int = 1) -> int:
        """Remove counters, returns actual amount removed"""
        current = self.counters.get(counter_type, 0)
        removed = min(amount, current)
        self.counters[counter_type] = current - removed
        if self.counters[counter_type] <= 0:
            self.counters.pop(counter_type, None)
        return removed

    def has_type(self, card_type: CardType) -> bool:
        """Check if this card has the given type"""
        return card_type in self.card_types

    def is_creature(self) -> bool:
        """Check if this card is a creature"""
        return self.has_type(CardType.CREATURE)

    def is_land(self) -> bool:
        """Check if this card is a land"""
        return self.has_type(CardType.LAND)

    def is_spell(self) -> bool:
        """Check if this card is a spell (not a land)"""
        return not self.is_land()

    def current_power(self) -> int:
        """Current power including modifications"""
        if not self.is_creature():
            return 0
        base_power = self.power or 0
        plus_counters = self.counters.get("+1/+1", 0)
        minus_counters = self.counters.get("-1/-1", 0)
        return max(0, base_power + plus_counters - minus_counters)

    def current_toughness(self) -> int:
        """Current toughness including modifications"""
        if not self.is_creature():
            return 0
        base_toughness = self.toughness or 0
        plus_counters = self.counters.get("+1/+1", 0)
        minus_counters = self.counters.get("-1/-1", 0)
        return max(0, base_toughness + plus_counters - minus_counters)

    def can_attack(self) -> bool:
        """Check if this creature can attack"""
        return (self.is_creature() and
                self.zone == Zone.BATTLEFIELD and
                not self.is_tapped and
                not self.summoning_sick)

    def can_block(self) -> bool:
        """Check if this creature can block"""
        return (self.is_creature() and
                self.zone == Zone.BATTLEFIELD and
                not self.is_tapped)

    def get_activated_abilities(self) -> List:
        """Get all activated abilities this card has"""
        return [ability for ability in self.abilities
                if hasattr(ability, 'ability_type') and ability.ability_type == "activated"]

    def get_triggered_abilities(self) -> List:
        """Get all triggered abilities this card has"""
        return [ability for ability in self.abilities
                if hasattr(ability, 'ability_type') and ability.ability_type == "triggered"]

    def reset_for_turn(self):
        """Reset card state for a new turn"""
        self.summoning_sick = False
        # Note: We don't untap here as that happens in the untap step

    def enters_battlefield(self):
        """Called when this card enters the battlefield"""
        self.zone = Zone.BATTLEFIELD
        if self.is_creature():
            self.summoning_sick = True

    def leaves_battlefield(self):
        """Called when this card leaves the battlefield"""
        self.is_tapped = False
        self.is_attacking = False
        self.is_blocking = False
        self.summoning_sick = True

    def copy(self) -> Card:
        """Create a copy of this card with a new ID"""
        new_card = Card(
            name=self.name,
            mana_cost=self.mana_cost.to_string(),
            type_line=self.type_line,
            oracle_text=self.oracle_text,
            colors=self.colors.copy(),
            power=str(self.power) if self.power is not None else None,
            toughness=str(self.toughness) if self.toughness is not None else None,
            rarity=self.rarity
        )
        return new_card

    # === NEW TARGETING AND SPELL RESOLUTION METHODS ===

    def get_target_filter(self) -> Optional[TargetFilter]:
        """Override in subclasses to define targeting requirements"""
        return None

    def requires_targets(self) -> bool:
        """Check if this spell requires targets to be cast"""
        return self.get_target_filter() is not None

    def resolve_spell(self, game_state: GameState, caster: Player, targets: List[Card]) -> bool:
        """Override in subclasses to define spell resolution effects"""
        # Default: just put in graveyard
        caster.graveyard.append(self)
        self.zone = Zone.GRAVEYARD
        return True

    def get_targetable_id(self) -> str:
        """Get the ID that can be used to target this card"""
        return self.id

    def get_display_info_for_targeting(self) -> str:
        """Get display string for targeting UI"""
        if self.is_creature():
            return f"{self.name} ({self.current_power()}/{self.current_toughness()}) [ID: {self.id[:8]}]"
        else:
            return f"{self.name} [ID: {self.id[:8]}]"

    @classmethod
    def get_card_name(cls) -> str:
        """Get the card name for this class - override in subclasses"""
        # This is a fallback - subclasses should override this
        return cls.__name__

    def __str__(self) -> str:
        """String representation for debugging"""
        return f"{self.name} ({self.id[:8]})"

    def __repr__(self) -> str:
        return self.__str__()


class ExileTracker:
    """Tracks cards exiled by specific sources"""

    def __init__(self):
        self.exiled_by_source = {}  # source_card_id -> list of exiled cards

    def exile_card(self, source_card: Card, target_card: Card):
        """Exile a card, tracking the source"""

        if source_card.id not in self.exiled_by_source:
            self.exiled_by_source[source_card.id] = []

        self.exiled_by_source[source_card.id].append(target_card)

        # Move card to exile zone
        if target_card.zone == Zone.BATTLEFIELD:
            target_card.controller.battlefield.remove(target_card)
            target_card.leaves_battlefield()
        elif target_card.zone == Zone.HAND:
            target_card.controller.hand.remove(target_card)
        elif target_card.zone == Zone.GRAVEYARD:
            target_card.controller.graveyard.remove(target_card)

        target_card.owner.exile.append(target_card)
        target_card.zone = Zone.EXILE

    def return_exiled_cards(self, source_card: Card):
        """Return all cards exiled by this source"""

        if source_card.id not in self.exiled_by_source:
            return []

        exiled_cards = self.exiled_by_source[source_card.id]
        returned_cards = []

        for card in exiled_cards:
            if card.zone == Zone.EXILE and card in card.owner.exile:
                # Return to battlefield under owner's control
                card.owner.exile.remove(card)
                card.owner.battlefield.append(card)
                card.zone = Zone.BATTLEFIELD
                card.controller = card.owner
                card.enters_battlefield()
                returned_cards.append(card)

                # Trigger ETB if it's a creature/permanent
                if hasattr(card, 'enters_battlefield'):
                    # This will be handled by the game state's trigger system
                    pass

        # Clear the tracking
        if source_card.id in self.exiled_by_source:
            del self.exiled_by_source[source_card.id]

        return returned_cards


class CardDatabase:
    """Database for storing and retrieving card definitions"""

    def __init__(self):
        self.cards: Dict[str, type] = {}

    def register_card(self, card_class: type):
        """Register a card class in the database"""
        # Use the class method to get the card name without creating an instance
        if hasattr(card_class, 'get_card_name'):
            card_name = card_class.get_card_name()
        else:
            # Fallback: create instance with empty kwargs
            try:
                temp_instance = card_class()
                card_name = temp_instance.name
            except Exception:
                # Last resort: use class name
                card_name = card_class.__name__

        self.cards[card_name] = card_class

    def create_card(self, name: str, **kwargs) -> Optional[Card]:
        """Create a card instance by name"""
        if name in self.cards:
            card_class = self.cards[name]
            return card_class(**kwargs)
        return None

    def get_all_card_names(self) -> List[str]:
        """Get all registered card names"""
        return list(self.cards.keys())


# Global instances
exile_tracker = ExileTracker()
card_database = CardDatabase()