# MTG LLM Benchmark

A text-based Magic: The Gathering game engine designed for language model agents, with an integrated benchmarking system for evaluating LLM performance in strategic card games.

## Overview

This project consists of two main components:

1. **Game Engine** - A complete MTG game implementation with card mechanics, game rules, and turn-based gameplay
2. **LLM Benchmark** - A system that tests language models by having them draft cards, build decks, and play games against each other

## Features

- **Complete MTG Engine**: Turn-based gameplay with proper phase management, mana system, combat, and card interactions
- **Card System**: Extensible card implementation supporting various MTG mechanics
- **LLM Integration**: Interface for language models to make game decisions through text-based interactions
- **Automated Drafting**: Integration with draft simulators to create sealed pools
- **Deck Building**: LLM-powered deck construction from card pools
- **Head-to-Head Games**: Automated gameplay between different language models

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure**
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml with your OpenRouter API key
   ```

3. **Run Benchmark**
   ```bash
   python main.py
   ```

## Architecture

### Game Engine (`engine/`)
- **Core Systems**: Game state management, turn structure, rules engine
- **Card System**: Individual card implementations and mechanics
- **Examples**: Sample games and basic AI agents

### Benchmark System (`benchmark/`)
- **Draft Loading**: Automated card pool generation from online draft simulators  
- **Deck Building**: LLM-powered deck construction with strategic reasoning
- **Agent Management**: Interface between game engine and language models
- **Result Tracking**: Performance analysis and game outcome recording

## Configuration

The system uses YAML configuration files to specify:
- Language model endpoints and API keys
- Agent configurations and model selections  
- Draft sources and formats
- Benchmark parameters

## Extending the System

- **Add Cards**: Implement new cards in `engine/cards/`
- **New Mechanics**: Extend core systems in `engine/core/`
- **Custom Agents**: Create specialized LLM agents in `benchmark/agents/`
- **Analysis Tools**: Add result processing in benchmark runners

## Requirements

- Python 3.8+
- OpenRouter API access
- Chrome/Chromium browser (for draft automation)
- See `requirements.txt` for full dependencies

## License

This project is for research and educational purposes. Magic: The Gathering is a trademark of Wizards of the Coast.