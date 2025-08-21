import requests
import json
import os
from typing import List, Dict, Any, Optional


class CardEnhancer:
    """Enhances card data with oracle information from Scryfall"""

    SCRYFALL_BULK_URL = "https://api.scryfall.com/bulk-data"
    ORACLE_CACHE_FILE = "oracle.json"

    def __init__(self, force_update: bool = False):
        self.oracle_data = None
        self.oracle_lookup = None
        self.force_update = force_update

    def fetch_oracle_data(self) -> List[Dict[str, Any]]:
        """Fetch oracle_cards bulk data from Scryfall and cache locally"""
        if os.path.exists(self.ORACLE_CACHE_FILE) and not self.force_update:
            print(f"[INFO] Loading oracle data from cache: {self.ORACLE_CACHE_FILE}")
            with open(self.ORACLE_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)

        if self.force_update and os.path.exists(self.ORACLE_CACHE_FILE):
            os.remove(self.ORACLE_CACHE_FILE)
            print("[INFO] Deleted old oracle.json cache")

        print("[INFO] Fetching oracle_cards URL from Scryfall...")
        resp = requests.get(self.SCRYFALL_BULK_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        oracle_entry = next((d for d in data["data"] if d.get("type") == "oracle_cards"), None)
        if not oracle_entry:
            raise RuntimeError("oracle_cards entry not found in Scryfall bulk data")

        download_url = oracle_entry["download_uri"]
        print(f"[INFO] Downloading oracle_cards data from {download_url} ...")
        oracle_resp = requests.get(download_url, timeout=120)
        oracle_resp.raise_for_status()
        oracle_data = oracle_resp.json()

        with open(self.ORACLE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(oracle_data, f)

        print(f"[INFO] Saved oracle data to {self.ORACLE_CACHE_FILE}")
        return oracle_data

    def build_oracle_lookup(self, oracle_cards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build lookup dictionaries for efficient card searching"""
        by_name = {}
        by_name_set = {}

        for card in oracle_cards:
            name = card.get("name", "").lower()
            if not name:
                continue

            by_name.setdefault(name, []).append(card)

            if "set" in card:
                by_name_set[f"{name}|{card['set'].lower()}"] = card

        return {"by_name": by_name, "by_name_set": by_name_set}

    def find_card(self, name: str, set_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find card data from oracle lookup"""
        if not self.oracle_lookup:
            return None

        name_lower = name.lower()
        candidates = []

        # Prefer set-specific match first if present
        if set_code:
            key = f"{name_lower}|{str(set_code).lower()}"
            if key in self.oracle_lookup["by_name_set"]:
                candidates.append(self.oracle_lookup["by_name_set"][key])

        # Fall back to all printings under the oracle name
        if name_lower in self.oracle_lookup["by_name"]:
            candidates.extend(self.oracle_lookup["by_name"][name_lower])

        # Return first candidate if found
        if candidates:
            return self.extract_fields(candidates[0])

        return None

    def extract_fields(self, card: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant fields from oracle card data"""
        fields = {}

        for k in ["mana_cost", "type_line", "oracle_text", "colors", "color_identity",
                  "power", "toughness", "loyalty", "rarity"]:
            v = card.get(k)
            if v not in (None, "", [], {}):
                fields[k] = v

        return fields

    def enhance_cards(self, card_names: List[str], set_code: str = "EOE") -> List[Dict[str, Any]]:
        """Enhance list of card names with oracle data"""
        if not self.oracle_data:
            self.oracle_data = self.fetch_oracle_data()
            self.oracle_lookup = self.build_oracle_lookup(self.oracle_data)

        enhanced = []
        not_found = 0

        for name in card_names:
            name = name.strip()
            if not name:
                continue

            card_data = self.find_card(name, set_code)

            if card_data:
                enhanced.append({"name": name, "quantity": 1, **card_data})
            else:
                not_found += 1
                print(f"[WARN] Not found in oracle: '{name}'")

        print(f"[INFO] Enhanced {len(enhanced)} cards. ({not_found} not found in oracle)")
        return enhanced
