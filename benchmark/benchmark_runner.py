import json
import os
from datetime import datetime

import yaml

from benchmark.agents.openrouter_agent import OpenRouterAgent
from benchmark.clients.openrouter_client import OpenRouterClient
from benchmark.draft.card_enhancer import CardEnhancer
from benchmark.draft.deck_builder import DeckBuilder
from benchmark.draft.draft_loader import DraftLoader


class BenchmarkRunner:
    """Orchestrates the complete MTG agent benchmark workflow including game simulation"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = None
        self.client = None
        self.output_dir = None

    def run(self):
        """Run the complete benchmark workflow including game simulation"""
        print("[INFO] Starting MTG Agent Benchmark...")

        # Step 1: Load configuration
        self._load_configuration()

        # Step 2: Initialize OpenRouter client
        self._initialize_client()

        # Step 3: Initialize agents
        agent1, agent2 = self._initialize_agents()

        # Step 4: Create output directory
        self._create_output_directory(agent1, agent2)

        # Step 5: Load drafts and enhance card data
        self._load_and_enhance_drafts(agent1, agent2)

        # Step 6: Build decks
        self._build_decks(agent1, agent2)

        # TODO Step 7: Initialize game simulator

        # TODO Step 8: Run the game simulation

        # TODO Step 9: Save results

        # TODO Step 10: Print results

    def _load_configuration(self):
        """Load configuration from YAML file"""
        print("[INFO] Loading configuration...")
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}")

    def _initialize_client(self):
        """Initialize OpenRouter client with API key"""
        print("[INFO] Initializing OpenRouter client...")
        api_key = self.config["openrouter"]["api_key"]
        if not api_key or api_key == "your_openrouter_api_key_here":
            raise ValueError("Please set a valid OpenRouter API key in config.yaml")

        self.client = OpenRouterClient(api_key)

    def _initialize_agents(self) -> tuple[OpenRouterAgent, OpenRouterAgent]:
        """Initialize both MTG agents"""
        print("[INFO] Initializing agents...")

        agent1_config = self.config["agents"]["agent1"]
        agent2_config = self.config["agents"]["agent2"]

        print(f"[INFO] Initializing {agent1_config['name']} with {agent1_config['model']}")
        agent1 = OpenRouterAgent(
            name=agent1_config["name"],
            model=agent1_config["model"],
            client=self.client
        )

        print(f"[INFO] Initializing {agent2_config['name']} with {agent2_config['model']}")
        agent2 = OpenRouterAgent(
            name=agent2_config["name"],
            model=agent2_config["model"],
            client=self.client
        )

        return agent1, agent2

    def _create_output_directory(self, agent1: OpenRouterAgent, agent2: OpenRouterAgent):
        """Create timestamped output directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_agent1_name = agent1.name.lower().replace(' ', '_').replace('-', '_')
        safe_agent2_name = agent2.name.lower().replace(' ', '_').replace('-', '_')

        self.output_dir = f"output/{safe_agent1_name}_vs_{safe_agent2_name}_{timestamp}"
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"[INFO] Created output directory: {self.output_dir}")

    def _load_and_enhance_drafts(self, agent1: OpenRouterAgent, agent2: OpenRouterAgent):
        """Load drafts for both agents and enhance card data"""
        print("[INFO] Loading and enhancing drafts...")

        # Initialize components
        draft_loader = DraftLoader(self.config["draftsim"]["base_url"])
        card_enhancer = CardEnhancer()
        draft_url = self.config["draftsim"]["draft_url"]

        print(f"[INFO] Loading draft from {draft_url}")

        # Load draft for agent 1
        print(f"[INFO] Loading draft for {agent1.name}...")
        agent1_cards = draft_loader.load_draft(draft_url)
        agent1.load_pool(agent1_cards)

        # Load draft for agent 2
        print(f"[INFO] Loading draft for {agent2.name}...")
        agent2_cards = draft_loader.load_draft(draft_url)
        agent2.load_pool(agent2_cards)

        # Enhance card data for both agents
        print(f"[INFO] Enhancing card data for {agent1.name}...")
        agent1_enhanced = card_enhancer.enhance_cards(agent1_cards)
        agent1.load_enhanced_pool(agent1_enhanced)

        print(f"[INFO] Enhancing card data for {agent2.name}...")
        agent2_enhanced = card_enhancer.enhance_cards(agent2_cards)
        agent2.load_enhanced_pool(agent2_enhanced)

        print(f"[INFO] Draft loading complete:")
        print(f"  - {agent1}")
        print(f"  - {agent2}")

        # Save draft exports, enhanced cards, and summary
        self._save_draft_exports(draft_loader, agent1, agent2)
        self._save_enhanced_cards(agent1, agent2)

    def _save_draft_exports(self, draft_loader: DraftLoader, agent1: OpenRouterAgent, agent2: OpenRouterAgent):
        """Save draft exports to output directory"""
        agent1_export = draft_loader.export_draft(agent1.pool)
        agent2_export = draft_loader.export_draft(agent2.pool)

        safe_agent1_name = agent1.name.lower().replace(' ', '_').replace('-', '_')
        safe_agent2_name = agent2.name.lower().replace(' ', '_').replace('-', '_')

        with open(f"{self.output_dir}/{safe_agent1_name}_draft.txt", 'w') as f:
            f.write(agent1_export)

        with open(f"{self.output_dir}/{safe_agent2_name}_draft.txt", 'w') as f:
            f.write(agent2_export)

        print(f"[INFO] Draft exports saved to output directory")

    def _save_enhanced_cards(self, agent1: OpenRouterAgent, agent2: OpenRouterAgent):
        """Save enhanced card data as JSON files"""
        safe_agent1_name = agent1.name.lower().replace(' ', '_').replace('-', '_')
        safe_agent2_name = agent2.name.lower().replace(' ', '_').replace('-', '_')

        # Save enhanced cards for agent 1
        agent1_enhanced_file = f"{self.output_dir}/{safe_agent1_name}_enhanced_cards.json"
        with open(agent1_enhanced_file, 'w', encoding='utf-8') as f:
            json.dump(agent1.enhanced_pool, f, indent=2, ensure_ascii=False)

        # Save enhanced cards for agent 2
        agent2_enhanced_file = f"{self.output_dir}/{safe_agent2_name}_enhanced_cards.json"
        with open(agent2_enhanced_file, 'w', encoding='utf-8') as f:
            json.dump(agent2.enhanced_pool, f, indent=2, ensure_ascii=False)

        print(f"[INFO] Enhanced card data saved:")
        print(f"  - {agent1_enhanced_file}")
        print(f"  - {agent2_enhanced_file}")

        # Save summary statistics
        self._save_card_statistics(agent1, agent2)

    def _save_card_statistics(self, agent1: OpenRouterAgent, agent2: OpenRouterAgent):
        """Save card pool statistics"""
        def get_card_stats(enhanced_pool):
            """Calculate statistics for an enhanced card pool"""
            stats = {
                "total_cards": len(enhanced_pool),
                "by_rarity": {},
                "by_color": {},
                "by_type": {},
                "mana_curve": {},
                "unique_cards": len(set(card["name"] for card in enhanced_pool))
            }

            for card in enhanced_pool:
                # Rarity stats
                rarity = card.get("rarity", "unknown")
                stats["by_rarity"][rarity] = stats["by_rarity"].get(rarity, 0) + 1

                # Color stats
                colors = card.get("colors", [])
                if not colors:
                    stats["by_color"]["colorless"] = stats["by_color"].get("colorless", 0) + 1
                else:
                    for color in colors:
                        stats["by_color"][color] = stats["by_color"].get(color, 0) + 1

                # Type stats
                type_line = card.get("type_line", "")
                if "Land" in type_line:
                    stats["by_type"]["Land"] = stats["by_type"].get("Land", 0) + 1
                elif "Creature" in type_line:
                    stats["by_type"]["Creature"] = stats["by_type"].get("Creature", 0) + 1
                elif "Instant" in type_line:
                    stats["by_type"]["Instant"] = stats["by_type"].get("Instant", 0) + 1
                elif "Sorcery" in type_line:
                    stats["by_type"]["Sorcery"] = stats["by_type"].get("Sorcery", 0) + 1
                else:
                    stats["by_type"]["Other"] = stats["by_type"].get("Other", 0) + 1

                # Mana curve (for non-lands)
                if "Land" not in type_line:
                    mana_cost = card.get("mana_cost", "")
                    # Simple CMC calculation - count {X} patterns
                    import re
                    cmc = len(re.findall(r'\{[^}]*\}', mana_cost))
                    stats["mana_curve"][str(cmc)] = stats["mana_curve"].get(str(cmc), 0) + 1

            return stats

        # Calculate stats for both agents
        agent1_stats = get_card_stats(agent1.enhanced_pool)
        agent2_stats = get_card_stats(agent2.enhanced_pool)

        # Create summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "agents": {
                agent1.name: {
                    "model": agent1.model,
                    "statistics": agent1_stats
                },
                agent2.name: {
                    "model": agent2.model,
                    "statistics": agent2_stats
                }
            }
        }

        # Save summary
        summary_file = f"{self.output_dir}/card_pool_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"[INFO] Card pool summary saved to {summary_file}")

    def _build_decks(self, agent1: OpenRouterAgent, agent2: OpenRouterAgent):
        """Build decks for both agents using their enhanced pools"""
        print(f"[INFO] Building decks...")

        deck_builder = DeckBuilder(self.client)

        # Build deck for agent 1
        self._build_agent_deck(deck_builder, agent1)

        # Build deck for agent 2
        self._build_agent_deck(deck_builder, agent2)

        # Save deck files after both decks are built
        self._save_decks(agent1, agent2)

    def _build_agent_deck(self, deck_builder: DeckBuilder, agent: OpenRouterAgent):
        """Build deck for a single agent"""
        print(f"[INFO] Building deck for {agent.name}...")

        deck_text = deck_builder.build_deck(
            agent.name,
            agent.model,
            agent.enhanced_pool
        )

        if not deck_text.startswith("ERROR:"):
            deck_cards = deck_builder.parse_deck_list(deck_text)
            validation = deck_builder.validate_deck(deck_cards)
            agent.set_deck(deck_cards, deck_text)

            print(f"[INFO] {agent.name} deck: {validation['total_cards']} cards " +
                  f"({validation['land_count']} lands, {validation['non_land_count']} spells)")

            if validation["issues"]:
                for issue in validation["issues"]:
                    print(f"[WARN] {agent.name}: {issue}")
        else:
            print(f"[ERROR] Failed to build deck for {agent.name}: {deck_text}")

    def _save_decks(self, agent1: OpenRouterAgent, agent2: OpenRouterAgent):
        """Save built decks to output directory"""
        safe_agent1_name = agent1.name.lower().replace(' ', '_').replace('-', '_')
        safe_agent2_name = agent2.name.lower().replace(' ', '_').replace('-', '_')

        # Save agent 1 deck
        if agent1.deck_text:
            deck1_file = f"{self.output_dir}/{safe_agent1_name}_deck.txt"
            with open(deck1_file, 'w', encoding='utf-8') as f:
                f.write(f"# Deck for {agent1.name} ({agent1.model})\n")
                f.write(f"# Built on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(agent1.deck_text)
            print(f"[INFO] {agent1.name} deck saved to {deck1_file}")

            # Save structured deck data as JSON
            deck1_json_file = f"{self.output_dir}/{safe_agent1_name}_deck.json"
            deck_data = {
                "agent_name": agent1.name,
                "model": agent1.model,
                "timestamp": datetime.now().isoformat(),
                "deck_cards": agent1.deck,
                "total_cards": agent1.get_deck_size(),
                "validation": self._get_deck_validation(agent1)
            }
            with open(deck1_json_file, 'w', encoding='utf-8') as f:
                json.dump(deck_data, f, indent=2, ensure_ascii=False)

        # Save agent 2 deck
        if agent2.deck_text:
            deck2_file = f"{self.output_dir}/{safe_agent2_name}_deck.txt"
            with open(deck2_file, 'w', encoding='utf-8') as f:
                f.write(f"# Deck for {agent2.name} ({agent2.model})\n")
                f.write(f"# Built on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(agent2.deck_text)
            print(f"[INFO] {agent2.name} deck saved to {deck2_file}")

            # Save structured deck data as JSON
            deck2_json_file = f"{self.output_dir}/{safe_agent2_name}_deck.json"
            deck_data = {
                "agent_name": agent2.name,
                "model": agent2.model,
                "timestamp": datetime.now().isoformat(),
                "deck_cards": agent2.deck,
                "total_cards": agent2.get_deck_size(),
                "validation": self._get_deck_validation(agent2)
            }
            with open(deck2_json_file, 'w', encoding='utf-8') as f:
                json.dump(deck_data, f, indent=2, ensure_ascii=False)

        # Create deck comparison summary
        self._save_deck_comparison(agent1, agent2)

    def _get_deck_validation(self, agent: OpenRouterAgent):
        """Get deck validation results for an agent"""
        if not agent.deck:
            return {"valid": False, "issues": ["No deck built"]}

        from benchmark.draft.deck_builder import DeckBuilder
        deck_builder = DeckBuilder(self.client)
        return deck_builder.validate_deck(agent.deck)

    def _save_deck_comparison(self, agent1: OpenRouterAgent, agent2: OpenRouterAgent):
        """Save deck comparison analysis"""
        def analyze_deck(agent):
            """Analyze deck composition"""
            if not agent.deck:
                return {"error": "No deck available"}

            analysis = {
                "total_cards": agent.get_deck_size(),
                "by_type": {},
                "by_color": {},
                "mana_curve": {},
                "average_cmc": 0
            }

            total_cmc = 0
            non_land_count = 0

            for card_info in agent.deck:
                card_name = card_info["name"]
                quantity = card_info["quantity"]

                # Find enhanced data for this card
                enhanced_card = next((c for c in agent.enhanced_pool if c["name"] == card_name), None)

                if enhanced_card:
                    type_line = enhanced_card.get("type_line", "")
                    colors = enhanced_card.get("colors", [])
                    mana_cost = enhanced_card.get("mana_cost", "")

                    # Type analysis
                    if "Land" in type_line:
                        analysis["by_type"]["Land"] = analysis["by_type"].get("Land", 0) + quantity
                    elif "Creature" in type_line:
                        analysis["by_type"]["Creature"] = analysis["by_type"].get("Creature", 0) + quantity
                    elif "Instant" in type_line:
                        analysis["by_type"]["Instant"] = analysis["by_type"].get("Instant", 0) + quantity
                    elif "Sorcery" in type_line:
                        analysis["by_type"]["Sorcery"] = analysis["by_type"].get("Sorcery", 0) + quantity
                    else:
                        analysis["by_type"]["Other"] = analysis["by_type"].get("Other", 0) + quantity

                    # Color analysis
                    if not colors:
                        analysis["by_color"]["Colorless"] = analysis["by_color"].get("Colorless", 0) + quantity
                    else:
                        for color in colors:
                            analysis["by_color"][color] = analysis["by_color"].get(color, 0) + quantity

                    # Mana curve (for non-lands)
                    if "Land" not in type_line:
                        import re
                        cmc = len(re.findall(r'\{[^}]*\}', mana_cost))
                        analysis["mana_curve"][str(cmc)] = analysis["mana_curve"].get(str(cmc), 0) + quantity
                        total_cmc += cmc * quantity
                        non_land_count += quantity

            # Calculate average CMC
            if non_land_count > 0:
                analysis["average_cmc"] = round(total_cmc / non_land_count, 2)

            return analysis

        # Analyze both decks
        agent1_analysis = analyze_deck(agent1)
        agent2_analysis = analyze_deck(agent2)

        # Create comparison
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "comparison": {
                agent1.name: {
                    "model": agent1.model,
                    "analysis": agent1_analysis
                },
                agent2.name: {
                    "model": agent2.model,
                    "analysis": agent2_analysis
                }
            }
        }

        # Save comparison
        comparison_file = f"{self.output_dir}/deck_comparison.json"
        with open(comparison_file, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)

        print(f"[INFO] Deck comparison saved to {comparison_file}")
