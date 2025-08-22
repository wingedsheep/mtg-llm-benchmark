import re
from pathlib import Path
from typing import List, Dict, Optional


def _sanitize_basename(name: str) -> str:
    """Make a safe filename and ensure .dck extension."""
    s = name.strip().replace(" ", "_")
    s = re.sub(r"[^A-Za-z0-9_.-]+", "", s)
    if not s.lower().endswith(".dck"):
        s += ".dck"
    return s


def to_forge_dck_text(deck_cards: List[Dict[str, int]], deck_display_name: str) -> str:
    """
    Forge-compatible deck format:

    [metadata]
    Name=My Deck Name
    [Main]
    4 Lightning Bolt
    20 Mountain
    """
    lines = []
    lines.append("[metadata]")
    lines.append(f"Name={deck_display_name}")
    lines.append("[Main]")

    for row in deck_cards:
        try:
            q = int(row["quantity"])
        except (KeyError, ValueError, TypeError):
            continue
        name = str(row.get("name", "")).strip()
        if not name or q <= 0:
            continue
        lines.append(f"{q} {name}")

    # no [Sideboard] section unless you have entries to write
    # ensure trailing newline
    return "\n".join(lines) + "\n"


def write_forge_dck(
        deck_cards: List[Dict[str, int]],
        deck_dir: Path,
        deck_basename: str,
        deck_display_name: Optional[str] = None,
) -> Path:
    """Write a .dck deck file to deck_dir and verify it was created."""
    deck_dir.mkdir(parents=True, exist_ok=True)

    filename = _sanitize_basename(deck_basename)
    deck_file = deck_dir / filename

    if not deck_display_name:
        deck_display_name = deck_basename.replace("_", " ").strip()

    deck_text = to_forge_dck_text(deck_cards, deck_display_name)
    deck_file.write_text(deck_text, encoding="utf-8")

    # Defensive: verify existence and non-empty
    if deck_file.stat().st_size == 0:
        raise IOError(f"Deck file {deck_file} was written but is empty.")

    return deck_file
