import os
from datetime import datetime

import yaml

from card_enhancer import CardEnhancer
from deck_builder import DeckBuilder
from draft_loader import DraftLoader
from mtg_agent import MTGAgent
from openrouter_client import OpenRouterClient


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

    def _initialize_agents(self) -> tuple[MTGAgent, MTGAgent]:
        """Initialize both MTG agents"""
        print("[INFO] Initializing agents...")

        agent1_config = self.config["agents"]["agent1"]
        agent2_config = self.config["agents"]["agent2"]

        print(f"[INFO] Initializing {agent1_config['name']} with {agent1_config['model']}")
        agent1 = MTGAgent(
            name=agent1_config["name"],
            model=agent1_config["model"],
            client=self.client
        )

        print(f"[INFO] Initializing {agent2_config['name']} with {agent2_config['model']}")
        agent2 = MTGAgent(
            name=agent2_config["name"],
            model=agent2_config["model"],
            client=self.client
        )

        return agent1, agent2

    def _create_output_directory(self, agent1: MTGAgent, agent2: MTGAgent):
        """Create timestamped output directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_agent1_name = agent1.name.lower().replace(' ', '_').replace('-', '_')
        safe_agent2_name = agent2.name.lower().replace(' ', '_').replace('-', '_')

        self.output_dir = f"output/{safe_agent1_name}_vs_{safe_agent2_name}_{timestamp}"
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"[INFO] Created output directory: {self.output_dir}")

    def _load_and_enhance_drafts(self, agent1: MTGAgent, agent2: MTGAgent):
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

        # Save draft exports
        self._save_draft_exports(draft_loader, agent1, agent2)

    def _save_draft_exports(self, draft_loader: DraftLoader, agent1: MTGAgent, agent2: MTGAgent):
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

    def _build_decks(self, agent1: MTGAgent, agent2: MTGAgent):
        """Build decks for both agents using their enhanced pools"""
        print(f"[INFO] Building decks...")

        deck_builder = DeckBuilder(self.client)

        # Build deck for agent 1
        self._build_agent_deck(deck_builder, agent1)

        # Build deck for agent 2
        self._build_agent_deck(deck_builder, agent2)

    def _build_agent_deck(self, deck_builder: DeckBuilder, agent: MTGAgent):
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
