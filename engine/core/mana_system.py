"""
Mana system for the MTG engine.
Handles mana costs, mana pools, and mana-related calculations.
"""

from dataclasses import dataclass
from typing import Dict

@dataclass
class ManaCost:
    """Represents mana cost like {1}{W}{U}"""
    generic: int = 0
    white: int = 0
    blue: int = 0
    black: int = 0
    red: int = 0
    green: int = 0
    colorless: int = 0

    @classmethod
    def from_string(cls, mana_str: str) -> 'ManaCost':
        """Parse mana cost string like '{1}{W}' into ManaCost object"""
        cost = cls()
        if not mana_str:
            return cost

        # Remove outer braces and split by inner braces
        mana_str = mana_str.strip('{}')
        symbols = []
        current = ""
        for char in mana_str:
            if char == '{':
                if current:
                    symbols.append(current)
                current = ""
            elif char == '}':
                if current:
                    symbols.append(current)
                current = ""
            else:
                current += char
        if current:
            symbols.append(current)

        for symbol in symbols:
            if symbol.isdigit():
                cost.generic += int(symbol)
            elif symbol == 'W':
                cost.white += 1
            elif symbol == 'U':
                cost.blue += 1
            elif symbol == 'B':
                cost.black += 1
            elif symbol == 'R':
                cost.red += 1
            elif symbol == 'G':
                cost.green += 1
            elif symbol == 'C':
                cost.colorless += 1

        return cost

    def total_cmc(self) -> int:
        """Total converted mana cost"""
        return (self.generic + self.white + self.blue + self.black +
                self.red + self.green + self.colorless)

    def to_string(self) -> str:
        """Format mana cost for display"""
        if self.total_cmc() == 0:
            return "{0}"

        parts = []
        if self.generic > 0:
            parts.append(f"{{{self.generic}}}")
        if self.white > 0:
            parts.extend(["{W}"] * self.white)
        if self.blue > 0:
            parts.extend(["{U}"] * self.blue)
        if self.black > 0:
            parts.extend(["{B}"] * self.black)
        if self.red > 0:
            parts.extend(["{R}"] * self.red)
        if self.green > 0:
            parts.extend(["{G}"] * self.green)
        if self.colorless > 0:
            parts.extend(["{C}"] * self.colorless)

        return ''.join(parts)

class ManaPool:
    """Manages a player's mana pool"""

    def __init__(self):
        self.mana: Dict[str, int] = {
            'white': 0,
            'blue': 0,
            'black': 0,
            'red': 0,
            'green': 0,
            'colorless': 0
        }

    def add_mana(self, color: str, amount: int = 1):
        """Add mana of a specific color"""
        if color in self.mana:
            self.mana[color] += amount

    def remove_mana(self, color: str, amount: int = 1) -> int:
        """Remove mana of a specific color, returns amount actually removed"""
        if color not in self.mana:
            return 0

        removed = min(amount, self.mana[color])
        self.mana[color] -= removed
        return removed

    def empty_pool(self):
        """Empty all mana from the pool"""
        for color in self.mana:
            self.mana[color] = 0

    def total_mana(self) -> int:
        """Total amount of mana in pool"""
        return sum(self.mana.values())

    def can_pay_cost(self, cost: ManaCost) -> bool:
        """Check if this pool can pay the given mana cost"""
        # Check colored requirements first
        if (cost.white > self.mana['white'] or
                cost.blue > self.mana['blue'] or
                cost.black > self.mana['black'] or
                cost.red > self.mana['red'] or
                cost.green > self.mana['green'] or
                cost.colorless > self.mana['colorless']):
            return False

        # Check generic cost
        colored_used = (cost.white + cost.blue + cost.black +
                        cost.red + cost.green + cost.colorless)
        remaining_mana = self.total_mana() - colored_used

        return remaining_mana >= cost.generic

    def pay_cost(self, cost: ManaCost) -> bool:
        """Attempt to pay a mana cost, returns True if successful"""
        if not self.can_pay_cost(cost):
            return False

        # Pay colored costs first
        self.remove_mana('white', cost.white)
        self.remove_mana('blue', cost.blue)
        self.remove_mana('black', cost.black)
        self.remove_mana('red', cost.red)
        self.remove_mana('green', cost.green)
        self.remove_mana('colorless', cost.colorless)

        # Pay generic cost with remaining mana (simple implementation)
        remaining_generic = cost.generic
        for color in ['white', 'blue', 'black', 'red', 'green', 'colorless']:
            if remaining_generic <= 0:
                break
            removed = self.remove_mana(color, min(remaining_generic, self.mana[color]))
            remaining_generic -= removed

        return True

    def get_display_string(self) -> str:
        """Get formatted string for display"""
        non_zero = []
        for color, amount in self.mana.items():
            if amount > 0:
                non_zero.append(f"{color}: {amount}")
        return ", ".join(non_zero) if non_zero else "empty"

    def copy(self) -> 'ManaPool':
        """Create a copy of this mana pool"""
        new_pool = ManaPool()
        new_pool.mana = self.mana.copy()
        return new_pool
