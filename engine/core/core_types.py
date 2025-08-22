"""
Core types and enums for the MTG engine.
Contains fundamental game concepts that other modules depend on.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any


class Zone(Enum):
    """Game zones where cards can exist"""
    LIBRARY = "library"
    HAND = "hand"
    BATTLEFIELD = "battlefield"
    GRAVEYARD = "graveyard"
    EXILE = "exile"
    STACK = "stack"


class Phase(Enum):
    """Game phases and steps"""
    UNTAP = "untap"
    UPKEEP = "upkeep"
    DRAW = "draw"
    MAIN1 = "main1"
    COMBAT_BEGIN = "combat_begin"
    COMBAT_DECLARE_ATTACKERS = "declare_attackers"
    COMBAT_DECLARE_BLOCKERS = "declare_blockers"
    COMBAT_DAMAGE = "combat_damage"
    COMBAT_END = "combat_end"
    MAIN2 = "main2"
    END = "end"
    CLEANUP = "cleanup"


class CardType(Enum):
    """Magic card types"""
    CREATURE = "creature"
    INSTANT = "instant"
    SORCERY = "sorcery"
    ENCHANTMENT = "enchantment"
    ARTIFACT = "artifact"
    PLANESWALKER = "planeswalker"
    LAND = "land"


class Color(Enum):
    """Magic colors"""
    WHITE = "white"
    BLUE = "blue"
    BLACK = "black"
    RED = "red"
    GREEN = "green"
    COLORLESS = "colorless"


@dataclass
class GameEvent:
    """Represents game events that can trigger abilities"""
    event_type: str
    data: Dict[str, Any]

    def __init__(self, event_type: str, **kwargs):
        self.event_type = event_type
        self.data = kwargs


@dataclass
class Counter:
    """Represents counters on permanents"""
    name: str
    amount: int = 1


# Color mapping for mana symbols
MANA_SYMBOL_TO_COLOR = {
    'W': Color.WHITE,
    'U': Color.BLUE,
    'B': Color.BLACK,
    'R': Color.RED,
    'G': Color.GREEN,
    'C': Color.COLORLESS
}

COLOR_TO_MANA_SYMBOL = {v: k for k, v in MANA_SYMBOL_TO_COLOR.items()}
