from typing import List, Dict, Any

from benchmark.clients.openrouter_client import OpenRouterClient


class OpenRouterAgent:
    """MTG playing agent using OpenRouter models"""

    def __init__(self, name: str, model: str, client: OpenRouterClient):
        self.name = name
        self.model = model
        self.client = client
        self.pool = []
        self.enhanced_pool = []
        self.deck = []
        self.deck_text = ""

    def load_pool(self, cards: List[str]):
        """Load the drafted card pool"""
        self.pool = cards

    def load_enhanced_pool(self, enhanced_cards: List[Dict[str, Any]]):
        """Load enhanced card data with oracle information"""
        self.enhanced_pool = enhanced_cards

    def set_deck(self, deck_cards: List[Dict[str, Any]], deck_text: str):
        """Set the built deck"""
        self.deck = deck_cards
        self.deck_text = deck_text

    def get_card_count(self) -> int:
        """Get number of cards in pool"""
        return len(self.pool)

    def get_deck_size(self) -> int:
        """Get total number of cards in deck"""
        if not self.deck:
            return 0
        return sum(card["quantity"] for card in self.deck)

    def __str__(self) -> str:
        deck_info = f", deck: {self.get_deck_size()} cards" if self.deck else ""
        return f"{self.name} ({self.model}) - pool: {self.get_card_count()} cards{deck_info}"
