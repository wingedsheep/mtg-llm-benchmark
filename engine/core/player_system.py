"""
Fixed player system for the MTG engine.
Manages player state, decks, and player actions with correct turn handling.
"""

import random
from typing import List, Optional

from engine.core.card_system import Card
from engine.core.core_types import Zone
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

    def can_cast_spell(self, spell: Card) -> bool:
        """Check if player can cast a spell"""
        if spell not in self.hand or spell.is_land():
            return False

        return self.mana_pool.can_pay_cost(spell.mana_cost)

    def cast_spell(self, spell: Card) -> bool:
        """Cast a spell from hand"""
        if not self.can_cast_spell(spell):
            return False

        # Pay mana cost
        if not self.mana_pool.pay_cost(spell.mana_cost):
            return False

        # Move spell to appropriate zone
        self.hand.remove(spell)

        if spell.is_creature():
            # Creatures go directly to battlefield
            self.battlefield.append(spell)
            spell.enters_battlefield()
        else:
            # Other spells go to stack (simplified - resolve immediately)
            # TODO: Implement proper stack
            self.resolve_spell(spell)

        return True

    def resolve_spell(self, spell: Card):
        """Resolve a spell (simplified)"""
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
        """Get total available mana (from lands and pool)"""
        lands_mana = len([land for land in self.get_lands() if not land.is_tapped])
        pool_mana = self.mana_pool.total_mana()
        return lands_mana + pool_mana

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
