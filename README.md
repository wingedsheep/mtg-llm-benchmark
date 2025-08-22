# MTG LLM Benchmark

A benchmarking system that evaluates language models by having them draft cards, build decks, and play Magic: The Gathering matches via Forge in headless mode.

## Overview

This project focuses on:
- **LLM Benchmarking** – Draft cards, build decks, and run head-to-head games between language models
- **Forge Integration** – Gameplay and rules are handled by the Forge engine (run in headless CLI simulation mode)

## Features

- **LLM Integration**: Interface for language models to make drafting and deckbuilding decisions
- **Automated Drafting**: Integration with draft simulators to create sealed pools
- **Deck Building**: LLM-powered deck construction from card pools
- **Head-to-Head Games**: Automated gameplay between different language models using Forge
- **Result Tracking**: Performance analysis and game outcome recording

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure**

   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml with your OpenRouter API key
   # Set forge.jar_path to your local Forge desktop jar
   ```

3. **Run Benchmark**

   ```bash
   python main.py
   ```

## Architecture

### Benchmark System (`benchmark/`)

* **Draft Loading**: Automated card pool generation from online draft simulators
* **Deck Building**: LLM-powered deck construction with strategic reasoning
* **Agent Management**: Interface between language models and the benchmark flow
* **Result Tracking**: Game outcomes and analysis

> Gameplay is delegated to **Forge** and executed in headless mode from the benchmark runner.

## Configuration

The system uses YAML configuration files to specify:

* Language model endpoints and API keys
* Agent configurations and model selections
* Draft sources and formats
* Benchmark parameters
* **Forge settings** (e.g., `forge.jar_path`, matches/games, format)

## Extending the System

* **Custom Agents**: Create specialized LLM agents in `benchmark/agents/`
* **Analysis Tools**: Add result processing in benchmark runners

## Requirements

* Python 3.8+
* OpenRouter API access
* Chrome/Chromium browser (for draft automation)
* **Java (for running Forge)**
* Forge desktop jar (configure `forge.jar_path` in `config.yaml`)

## License

This project is for research and educational purposes. Magic: The Gathering is a trademark of Wizards of the Coast.
