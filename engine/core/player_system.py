"""
Fixed player system for the MTG engine.
Manages player state, decks, and player actions with correct turn handling.
Updated with proper mana payment and spell casting integration.
"""

import random
from typing import List, Optional

from engine.core.card_system import Card
from engine.core.core_types import Zone
from engine.core.display_system import game_logger
from engine.core.mana_system import ManaPool


class Player:
    """Represents a player in the game"""

    def __init__(self, name: str, deck: List[Card]):
        self.name = name
        self.life = 20

        # Card zones
        self.library = deck.copy()
        self.hand: List[Card] = []
        self.battlefield: List[Card] = []
        self.graveyard: List[Card] = []
        self.exile: List[Card] = []

        # Mana system
        self.mana_pool = ManaPool()

        # Game state tracking
        self.lands_played_this_turn = 0
        self.max_hand_size = 7
        self.has_played_land_this_turn = False
        self.turn_count = 0  # Track how many turns this player has taken

        # Setup deck
        self._setup_deck()

    def _setup_deck(self):
        """Initialize deck - set ownership and shuffle"""
        # Set ownership
        for card in self.library:
            card.owner = self
            card.controller = self
            card.zone = Zone.LIBRARY

        # Shuffle library
        random.shuffle(self.library)

    def draw_card(self) -> Optional[Card]:
        """Draw a card from library to hand"""
        if not self.library:
            # Player loses when they can't draw
            self.life = 0
            return None

        card = self.library.pop(0)
        card.zone = Zone.HAND
        self.hand.append(card)
        return card

    def draw_cards(self, amount: int) -> List[Card]:
        """Draw multiple cards"""
        drawn = []
        for _ in range(amount):
            card = self.draw_card()
            if card:
                drawn.append(card)
            else:
                break
        return drawn

    def mulligan(self, cards_to_keep: int = 6):
        """Perform a mulligan (simplified)"""
        # Put hand back into library
        for card in self.hand:
            card.zone = Zone.LIBRARY
            self.library.append(card)
        self.hand.clear()

        # Shuffle and draw new hand
        random.shuffle(self.library)
        self.draw_cards(cards_to_keep)

    def play_land(self, land: Card) -> bool:
        """Play a land from hand to battlefield"""
        if (land not in self.hand or
                not land.is_land() or
                self.has_played_land_this_turn):
            return False

        # Move land to battlefield
        self.hand.remove(land)
        self.battlefield.append(land)
        land.enters_battlefield()

        self.has_played_land_this_turn = True
        self.lands_played_this_turn += 1

        return True

    def _get_available_mana_by_color(self) -> dict:
        """Get available mana by color from mana pool + untapped lands"""
        available = {
            'white': self.mana_pool.mana['white'],
            'blue': self.mana_pool.mana['blue'],
            'black': self.mana_pool.mana['black'],
            'red': self.mana_pool.mana['red'],
            'green': self.mana_pool.mana['green'],
            'colorless': self.mana_pool.mana['colorless']
        }

        # Add what untapped lands can produce
        for land in self.get_lands():
            if not land.is_tapped:
                if "Plains" in land.name:
                    available['white'] += 1
                elif "Island" in land.name:
                    available['blue'] += 1
                elif "Swamp" in land.name:
                    available['black'] += 1
                elif "Mountain" in land.name:
                    available['red'] += 1
                elif "Forest" in land.name:
                    available['green'] += 1
                else:
                    available['colorless'] += 1

        return available

    def _can_pay_mana_cost(self, cost) -> bool:
        """Check if we can pay a mana cost with current mana pool + untapped lands"""
        # Start with mana already in pool
        available = {
            'white': self.mana_pool.mana['white'],
            'blue': self.mana_pool.mana['blue'],
            'black': self.mana_pool.mana['black'],
            'red': self.mana_pool.mana['red'],
            'green': self.mana_pool.mana['green'],
            'colorless': self.mana_pool.mana['colorless']
        }

        # Add what untapped lands can produce
        for land in self.get_lands():
            if not land.is_tapped:
                if "Plains" in land.name:
                    available['white'] += 1
                elif "Island" in land.name:
                    available['blue'] += 1
                elif "Swamp" in land.name:
                    available['black'] += 1
                elif "Mountain" in land.name:
                    available['red'] += 1
                elif "Forest" in land.name:
                    available['green'] += 1
                else:
                    available['colorless'] += 1

        # Check if we have enough of each specific color
        if (cost.white > available['white'] or
                cost.blue > available['blue'] or
                cost.black > available['black'] or
                cost.red > available['red'] or
                cost.green > available['green']):
            return False

        # If there's a colorless requirement (rare, for Eldrazi), check it
        if hasattr(cost, 'colorless') and cost.colorless > 0:
            if cost.colorless > available['colorless']:
                return False

        # Calculate remaining mana after paying colored (and colorless) costs
        remaining_mana = {
            'white': available['white'] - cost.white,
            'blue': available['blue'] - cost.blue,
            'black': available['black'] - cost.black,
            'red': available['red'] - cost.red,
            'green': available['green'] - cost.green,
            'colorless': available['colorless'] - getattr(cost, 'colorless', 0)
        }

        # Total remaining mana can pay for generic costs
        total_remaining = sum(remaining_mana.values())

        return total_remaining >= cost.generic

    def get_total_available_mana(self) -> int:
        """Get total available mana from pool + untapped lands (for display only)"""
        pool_mana = self.mana_pool.total_mana()

        # Count untapped lands
        untapped_lands = len([land for land in self.get_lands() if not land.is_tapped])

        return pool_mana + untapped_lands

    def can_cast_spell(self, spell: Card) -> bool:
        """Check if player can cast a spell"""
        if spell not in self.hand or spell.is_land():
            return False

        return self._can_pay_mana_cost(spell.mana_cost)

    def tap_lands_for_spell(self, spell: Card) -> bool:
        """Tap untapped lands to pay for a spell's mana cost"""
        if not self._can_pay_mana_cost(spell.mana_cost):
            return False

        cost = spell.mana_cost

        # First, check what we need vs what's already in the pool
        needed = {
            'white': max(0, cost.white - self.mana_pool.mana['white']),
            'blue': max(0, cost.blue - self.mana_pool.mana['blue']),
            'black': max(0, cost.black - self.mana_pool.mana['black']),
            'red': max(0, cost.red - self.mana_pool.mana['red']),
            'green': max(0, cost.green - self.mana_pool.mana['green']),
            'colorless': max(0, getattr(cost, 'colorless', 0) - self.mana_pool.mana['colorless'])
        }

        # Calculate generic mana needed after colored requirements
        generic_needed = cost.generic

        # If we don't need to tap any lands (pool has everything), return True
        total_needed = sum(needed.values()) + generic_needed
        if total_needed == 0:
            return True

        untapped_lands = [land for land in self.get_lands() if not land.is_tapped]
        lands_to_tap = []

        # Helper to find and reserve a land of specific type
        def find_land_for_color(color_name: str, needed_amount: int) -> int:
            remaining = needed_amount
            for land in untapped_lands:
                if remaining <= 0:
                    break
                if color_name in land.name and land not in lands_to_tap:
                    lands_to_tap.append(land)
                    remaining -= 1
            return remaining

        # Pay colored costs first (only what we need beyond pool)
        white_remaining = find_land_for_color("Plains", needed['white'])
        blue_remaining = find_land_for_color("Island", needed['blue'])
        black_remaining = find_land_for_color("Swamp", needed['black'])
        red_remaining = find_land_for_color("Mountain", needed['red'])
        green_remaining = find_land_for_color("Forest", needed['green'])

        # For generic cost, first see what's left in pool after colored costs
        pool_available_for_generic = (
                max(0, self.mana_pool.mana['white'] - cost.white) +
                max(0, self.mana_pool.mana['blue'] - cost.blue) +
                max(0, self.mana_pool.mana['black'] - cost.black) +
                max(0, self.mana_pool.mana['red'] - cost.red) +
                max(0, self.mana_pool.mana['green'] - cost.green) +
                max(0, self.mana_pool.mana['colorless'] - getattr(cost, 'colorless', 0))
        )

        generic_remaining = max(0, generic_needed - pool_available_for_generic)

        # Pay remaining generic cost with any untapped lands
        for land in untapped_lands:
            if generic_remaining <= 0:
                break
            if land not in lands_to_tap:
                lands_to_tap.append(land)
                generic_remaining -= 1

        # Final validation
        if (white_remaining > 0 or blue_remaining > 0 or black_remaining > 0 or
                red_remaining > 0 or green_remaining > 0 or generic_remaining > 0):
            game_logger.log_event(f"Not enough untapped lands to cast {spell.name}")
            return False

        # Actually tap the lands and add mana
        for land in lands_to_tap:
            land.is_tapped = True

            if "Plains" in land.name:
                self.mana_pool.add_mana('white')
            elif "Island" in land.name:
                self.mana_pool.add_mana('blue')
            elif "Swamp" in land.name:
                self.mana_pool.add_mana('black')
            elif "Mountain" in land.name:
                self.mana_pool.add_mana('red')
            elif "Forest" in land.name:
                self.mana_pool.add_mana('green')
            else:
                self.mana_pool.add_mana('colorless')

        if lands_to_tap:
            land_names = [land.name for land in lands_to_tap]
            game_logger.log_event(f"{self.name} taps {len(lands_to_tap)} lands: {', '.join(land_names)}")

        return True

    def cast_spell(self, spell: Card) -> bool:
        """Cast a spell from hand - this is the simple version for backwards compatibility"""
        if not self.can_cast_spell(spell):
            return False

        # Tap lands for mana if needed
        if not self.tap_lands_for_spell(spell):
            return False

        # Pay mana cost
        if not self.mana_pool.pay_cost(spell.mana_cost):
            return False

        # Remove spell from hand - the spell system will handle the rest
        # This method is now mainly used for creatures that go directly to battlefield
        if spell.is_creature():
            self.hand.remove(spell)
            self.battlefield.append(spell)
            spell.zone = Zone.BATTLEFIELD
            spell.controller = self
            spell.enters_battlefield()
            return True
        else:
            # Non-creatures should use spell_system.cast_spell_with_targets instead
            # This is just for backwards compatibility
            self.hand.remove(spell)
            self.resolve_spell(spell)
            return True

    def resolve_spell(self, spell: Card):
        """Resolve a spell (simplified fallback)"""
        # Execute spell effects here
        # For now, just put non-permanents in graveyard
        if not spell.is_creature():
            self.graveyard.append(spell)
            spell.zone = Zone.GRAVEYARD

    def sacrifice_permanent(self, permanent: Card) -> bool:
        """Sacrifice a permanent"""
        if permanent not in self.battlefield:
            return False

        self.battlefield.remove(permanent)
        self.graveyard.append(permanent)
        permanent.zone = Zone.GRAVEYARD
        permanent.leaves_battlefield()

        return True

    def get_creatures(self) -> List[Card]:
        """Get all creatures on battlefield"""
        return [card for card in self.battlefield if card.is_creature()]

    def get_lands(self) -> List[Card]:
        """Get all lands on battlefield"""
        return [card for card in self.battlefield if card.is_land()]

    def get_untapped_creatures(self) -> List[Card]:
        """Get all untapped creatures"""
        return [card for card in self.get_creatures() if not card.is_tapped]

    def get_attackers(self) -> List[Card]:
        """Get all attacking creatures"""
        return [card for card in self.get_creatures() if card.is_attacking]

    def get_blockers(self) -> List[Card]:
        """Get all blocking creatures"""
        return [card for card in self.get_creatures() if card.is_blocking]

    def lose_life(self, amount: int):
        """Lose life"""
        self.life -= amount
        if self.life < 0:
            self.life = 0

    def gain_life(self, amount: int):
        """Gain life"""
        self.life += amount

    def start_turn(self):
        """Reset turn-based state"""
        self.has_played_land_this_turn = False
        self.lands_played_this_turn = 0
        self.turn_count += 1

        # Reset creatures' summoning sickness
        for card in self.battlefield:
            card.reset_for_turn()

    def untap_step(self):
        """Untap all permanents"""
        for card in self.battlefield:
            card.is_tapped = False

    def upkeep_step(self):
        """Upkeep step - trigger upkeep abilities"""
        # TODO: Implement upkeep triggers
        pass

    def draw_step(self):
        """Draw step - draw a card"""
        self.draw_card()

    def cleanup_step(self):
        """Cleanup step - discard to hand size, remove damage, etc."""
        # Discard to maximum hand size
        while len(self.hand) > self.max_hand_size:
            # TODO: Implement choice for which cards to discard
            # For now, discard randomly
            if self.hand:
                discarded = self.hand.pop(random.randint(0, len(self.hand) - 1))
                self.graveyard.append(discarded)
                discarded.zone = Zone.GRAVEYARD

        # Empty mana pool
        self.mana_pool.empty_pool()

    def is_alive(self) -> bool:
        """Check if player is still alive"""
        return self.life > 0

    def get_available_mana(self) -> int:
        """Get total available mana (from lands and pool) - deprecated, use get_total_available_mana"""
        return self.get_total_available_mana()

    def tap_lands_for_mana(self, amount: int, color: str = None) -> int:
        """Tap lands to add mana to pool, returns amount actually added"""
        lands = [land for land in self.get_lands() if not land.is_tapped]

        # For simplicity, assume all lands can produce any color
        tapped = 0
        for land in lands[:amount]:
            if land.abilities:  # Land has mana ability
                land.is_tapped = True
                # Add appropriate mana based on land type
                if "Plains" in land.name:
                    self.mana_pool.add_mana('white')
                elif "Island" in land.name:
                    self.mana_pool.add_mana('blue')
                elif "Swamp" in land.name:
                    self.mana_pool.add_mana('black')
                elif "Mountain" in land.name:
                    self.mana_pool.add_mana('red')
                elif "Forest" in land.name:
                    self.mana_pool.add_mana('green')
                else:
                    self.mana_pool.add_mana('colorless')
                tapped += 1

        return tapped

    def __str__(self) -> str:
        return f"Player({self.name}, Life: {self.life})"

    def __repr__(self) -> str:
        return self.__str__()


class PlayerManager:
    """Manages multiple players in a game"""

    def __init__(self, players: List[Player]):
        self.players = players
        self.turn_order = list(range(len(players)))

    def get_player(self, index: int) -> Player:
        """Get player by index"""
        return self.players[index]

    def get_opponents(self, player: Player) -> List[Player]:
        """Get all opponents of a given player"""
        return [p for p in self.players if p != player]

    def get_next_player(self, current_player_index: int) -> int:
        """Get the index of the next player in turn order"""
        return (current_player_index + 1) % len(self.players)

    def all_players_alive(self) -> bool:
        """Check if all players are still alive"""
        return all(player.is_alive() for player in self.players)

    def get_winner(self) -> Optional[Player]:
        """Get the winner if there is one"""
        alive_players = [p for p in self.players if p.is_alive()]
        if len(alive_players) == 1:
            return alive_players[0]
        return None
