from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
from typing import List, Dict, Any


class DraftLoader:
    """Handles loading and exporting draft data from Draftsim using browser automation"""

    def __init__(self, base_url: str, headless: bool = True):
        self.base_url = base_url
        self.headless = headless
        self.driver = None

    def _setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver

    def load_draft(self, draft_url: str) -> List[str]:
        """Load draft from Draftsim URL by automating the draft process and using deck_text() function"""
        try:
            if not self.driver:
                self._setup_driver()

            print(f"[INFO] Opening draft URL: {draft_url}")
            self.driver.get(draft_url)

            # Wait for page to load
            wait = WebDriverWait(self.driver, 30)

            # Wait for the JavaScript to load and initialize
            print("[INFO] Waiting for page to fully load...")
            time.sleep(5)

            # Check if we're in sealed format by looking for the collection container
            try:
                collection_container = wait.until(
                    EC.presence_of_element_located((By.ID, "collection-container"))
                )
                print("[INFO] Sealed pool detected - cards are loaded")

                # Wait a bit more for all cards to be loaded
                time.sleep(2)

                # Execute the deck_text() function directly to get the deck list
                print("[INFO] Executing deck_text() function to get card list...")

                # First, we need to ensure the draft object is available
                deck_list_text = self.driver.execute_script("""
                    try {
                        // Check if draft object exists and has players
                        if (typeof draft === 'undefined' || !draft.players || !draft.players[0]) {
                            return 'ERROR: Draft object not found or not initialized';
                        }

                        // Get the card names from the collection (pool)
                        let deck_names = [];
                        let collection = draft.players[0].collection || [];

                        for (var i = 0; i < collection.length; i++) {
                            // Strip out numbers at end of basic lands and clean up names
                            let cardName = collection[i].name.replace(new RegExp("_[0-9]", "g"), '');
                            deck_names.push(cardName);
                        }

                        // Get the unique names and counts of each card
                        let counts = {};
                        deck_names.forEach(function(cardName) {
                            counts[cardName] = (counts[cardName] || 0) + 1;
                        });

                        // Create the deck text output
                        let deckText = "";
                        let uniqueCards = [...new Set(deck_names)];

                        for (var i = 0; i < uniqueCards.length; i++) {
                            let cardName = uniqueCards[i]
                                .replace(/_/g, ' ')
                                .replace(/'/g, "'"); // Fix apostrophes
                            deckText += counts[uniqueCards[i]] + " " + cardName + "\\n";
                        }

                        return deckText.trim();

                    } catch (error) {
                        return 'ERROR: ' + error.toString();
                    }
                """)

                if deck_list_text.startswith('ERROR:'):
                    print(f"[ERROR] JavaScript execution failed: {deck_list_text}")
                    # Fallback to DOM parsing
                    return self._extract_cards_from_dom()

                if not deck_list_text.strip():
                    print("[WARN] No cards found in collection, trying DOM extraction")
                    return self._extract_cards_from_dom()

                # Parse the deck list text into individual card names
                cards = []
                for line in deck_list_text.strip().split('\n'):
                    line = line.strip()
                    if line:
                        # Parse "quantity cardname" format
                        parts = line.split(' ', 1)
                        if len(parts) >= 2:
                            try:
                                quantity = int(parts[0])
                                card_name = parts[1].strip()
                                # Add the card multiple times based on quantity
                                for _ in range(quantity):
                                    cards.append(card_name)
                            except ValueError:
                                # If we can't parse quantity, just add the whole line as card name
                                cards.append(line)
                        else:
                            cards.append(line)

                print(f"[INFO] Successfully extracted {len(cards)} cards from sealed pool")
                return cards

            except TimeoutException:
                print("[ERROR] Timeout waiting for collection container")
                raise Exception("Timeout waiting for sealed pool to load")

        except Exception as e:
            print(f"[ERROR] Failed to load draft: {str(e)}")
            raise Exception(f"Failed to load draft: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def _extract_cards_from_dom(self) -> List[str]:
        """Fallback method to extract cards directly from DOM"""
        try:
            print("[INFO] Attempting DOM extraction as fallback...")
            deck_elements = self.driver.find_elements(By.XPATH, "//li[contains(@class, 'collection-card')]")

            if not deck_elements:
                print("[WARN] No collection cards found in DOM")
                return []

            cards = []
            for element in deck_elements:
                # Try to get card name from onmouseover attribute
                onmouseover = element.get_attribute("onmouseover")
                if onmouseover:
                    # Extract card name from image path
                    match = re.search(r'Images/EOE/([^"]+)\.jpg', onmouseover)
                    if match:
                        card_name = match.group(1).replace('_', ' ').replace('%27', "'")
                        # Clean up card name
                        card_name = card_name.replace('_foil', '').replace('_', ' ')
                        cards.append(card_name)

            print(f"[INFO] DOM extraction found {len(cards)} cards")
            return cards

        except Exception as e:
            print(f"[ERROR] DOM extraction failed: {e}")
            return []

    def export_draft(self, cards: List[str]) -> str:
        """Export draft as text format"""
        if not cards:
            return "No cards in draft"

        export_text = "Draft Export:\n" + "=" * 50 + "\n"
        for i, card in enumerate(cards, 1):
            export_text += f"{i:2d}. {card}\n"

        export_text += f"\nTotal cards: {len(cards)}"
        return export_text

    def __del__(self):
        """Cleanup driver on destruction"""
        if self.driver:
            self.driver.quit()
