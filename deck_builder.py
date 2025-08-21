from typing import List, Dict, Any
from openrouter_client import OpenRouterClient


class DeckBuilder:
    """Handles building decks from enhanced card pools using OpenRouter models"""

    def __init__(self, client: OpenRouterClient):
        self.client = client

    def format_cards_for_prompt(self, enhanced_cards: List[Dict[str, Any]]) -> str:
        """Format enhanced cards for the AI prompt"""
        if not enhanced_cards:
            return "No cards available"

        cards_text = ""
        for card in enhanced_cards:
            card_name = card.get("name", "Unknown Card")
            quantity = card.get("quantity", 1)

            # Add basic card info
            cards_text += f"{quantity}x {card_name}"

            # Add mana cost if available
            if card.get("mana_cost"):
                cards_text += f" ({card['mana_cost']})"

            # Add type line if available
            if card.get("type_line"):
                cards_text += f" - {card['type_line']}"

            # Add power/toughness for creatures
            if card.get("power") is not None and card.get("toughness") is not None:
                cards_text += f" [{card['power']}/{card['toughness']}]"

            # Add rarity
            if card.get("rarity"):
                cards_text += f" ({card['rarity']})"

            cards_text += "\n"

        return cards_text.strip()

    def build_deck(self, agent_name: str, model: str, enhanced_cards: List[Dict[str, Any]]) -> str:
        """Build a deck using the AI model"""
        try:
            # Format cards for the prompt
            cards_text = self.format_cards_for_prompt(enhanced_cards)

            # Create the prompt
            prompt = f"""This is your sealed draft with which you are going to play against other language models. Please create the best deck possible with at least 40 cards including lands. You can use as many basic lands as you want.

Your card pool:
{cards_text}

Available basic lands:
- Plains (White)
- Island (Blue) 
- Swamp (Black)
- Mountain (Red)
- Forest (Green)

Please respond with your deck list in the following format. 
Make sure to have exactly ONE code block in your response, which should contain the decklist.
You can write something about your deck, but not in the codeblock. This should contain only the decklist.

The exported text for each card in the deck follows a consistent structure:
1. **Quantity** The number of copies of a specific card in the deck.
2. **Card Name** The full name of the Magic: The Gathering card.

Example format:
```
4 Healer's Hawk
4 Leonin Vanguard
4 Ajani's Pridemate
10 Plains
```

Build the most competitive deck with at least 40 cards possible from your pool."""

            print(f"[INFO] Building deck for {agent_name} using {model}...")

            # Make the API call
            response = self.client.create_completion(
                model=model,
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.7,
                max_tokens=8000
            )

            # Extract the deck list from response
            deck_text = response.choices[0].message.content.strip()

            print(f"[INFO] Deck built successfully for {agent_name}")
            return deck_text

        except Exception as e:
            print(f"[ERROR] Failed to build deck for {agent_name}: {e}")
            return f"ERROR: Failed to build deck - {str(e)}"

    def parse_deck_list(self, deck_text: str) -> List[Dict[str, Any]]:
        """Parse deck list text into structured format"""
        deck_cards = []

        # Extract content from code block if present
        lines = deck_text.split('\n')
        in_code_block = False
        code_block_content = []

        for line in lines:
            line = line.strip()

            # Handle code block markers
            if line.startswith('```'):
                if not in_code_block:
                    # Starting a code block
                    in_code_block = True
                    continue
                else:
                    # Ending a code block - stop processing after first block
                    break

            # If we're in a code block, collect the content
            if in_code_block:
                code_block_content.append(line)

        # Use code block content if we found one, otherwise use original text
        if code_block_content:
            lines_to_parse = code_block_content
        else:
            lines_to_parse = [line.strip() for line in deck_text.split('\n')]

        # Parse the deck list
        for line in lines_to_parse:
            if not line or line.lower() in ['deck', 'deck list:', 'decklist:']:
                continue

            # Try to parse "quantity cardname" format
            parts = line.split(' ', 1)
            if len(parts) >= 2:
                try:
                    quantity = int(parts[0])
                    card_name = parts[1].strip()

                    deck_cards.append({
                        "quantity": quantity,
                        "name": card_name
                    })
                except ValueError:
                    # If we can't parse quantity, skip this line
                    print(f"[WARN] Could not parse deck line: {line}")
                    continue

        return deck_cards

    def validate_deck(self, deck_cards: List[Dict[str, Any]], min_cards: int = 40) -> Dict[str, Any]:
        """Validate deck composition"""
        total_cards = sum(card["quantity"] for card in deck_cards)

        # Count basic lands
        basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest"]
        land_count = sum(
            card["quantity"] for card in deck_cards
            if card["name"] in basic_lands
        )

        # Count non-land cards
        non_land_count = total_cards - land_count

        validation = {
            "valid": True,
            "total_cards": total_cards,
            "land_count": land_count,
            "non_land_count": non_land_count,
            "issues": []
        }

        if total_cards < min_cards:
            validation["valid"] = False
            validation["issues"].append(f"Deck has only {total_cards} cards, minimum is {min_cards}")

        return validation
