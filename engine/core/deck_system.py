"""
Deck system for the MTG engine.
Handles deck creation, shuffling, and basic deck operations.
"""

import random
from dataclasses import dataclass
from typing import List, Dict, Any

from engine.core.card_system import Card
from engine.core.core_types import Zone
from engine.core.display_system import game_logger


@dataclass
class DeckConfiguration:
    """Configuration for creating a deck"""
    card_specifications: List[Dict[str, Any]]  # List of {card_class: Class, quantity: int}

    def get_total_cards(self) -> int:
        """Get total number of cards in this deck configuration"""
        return sum(spec['quantity'] for spec in self.card_specifications)


class DeckSystem:
    """Manages deck operations like shuffling, drawing, and card placement"""

    def __init__(self):
        pass

    def create_deck_from_config(self, config: DeckConfiguration) -> List[Card]:
        """Create a deck from a configuration"""
        deck = []

        for spec in config.card_specifications:
            card_class = spec['card_class']
            quantity = spec['quantity']

            for _ in range(quantity):
                card = card_class()
                deck.append(card)

        return deck

    def shuffle_deck(self, deck: List[Card]) -> None:
        """Shuffle a deck in place"""
        random.shuffle(deck)
        game_logger.log_event("Deck shuffled")

    def draw_cards(self, deck: List[Card], hand: List[Card], count: int) -> List[Card]:
        """Draw cards from deck to hand, returns cards drawn"""
        drawn_cards = []

        for _ in range(count):
            if deck:
                card = deck.pop(0)  # Draw from top
                card.zone = Zone.HAND
                hand.append(card)
                drawn_cards.append(card)
            else:
                break  # No more cards to draw

        return drawn_cards

    def put_cards_bottom(self, deck: List[Card], cards: List[Card]) -> None:
        """Put cards at the bottom of the deck"""
        for card in cards:
            card.zone = Zone.LIBRARY
            deck.append(card)  # Add to bottom

    def put_cards_top(self, deck: List[Card], cards: List[Card]) -> None:
        """Put cards on top of the deck"""
        for card in reversed(cards):  # Reverse to maintain order
            card.zone = Zone.LIBRARY
            deck.insert(0, card)  # Add to top

    def put_card_at_position(self, deck: List[Card], card: Card, position: int) -> None:
        """Put a card at a specific position in the deck (0 = top)"""
        card.zone = Zone.LIBRARY
        position = max(0, min(position, len(deck)))  # Clamp position
        deck.insert(position, card)

    def peek_top_cards(self, deck: List[Card], count: int) -> List[Card]:
        """Look at the top N cards without removing them"""
        return deck[:min(count, len(deck))]

    def remove_cards_from_deck(self, deck: List[Card], cards: List[Card]) -> List[Card]:
        """Remove specific cards from deck, returns cards that were found and removed"""
        removed = []
        for card in cards:
            if card in deck:
                deck.remove(card)
                removed.append(card)
        return removed


# Singleton deck system
deck_system = DeckSystem()
