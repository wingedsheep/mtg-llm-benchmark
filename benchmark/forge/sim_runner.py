import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional

# Patterns aimed at Forge sim output
PAT_GAME_RESULT_WIN = re.compile(r"Game Result:.*?\.\s+Ai\((\d+)\)-.*?has won!", re.IGNORECASE)
PAT_OUTCOME_WIN = re.compile(r"Game outcome:.*?Ai\((\d+)\)-.*?has won", re.IGNORECASE)


@dataclass
class ForgeSimConfig:
    java_bin: str
    forge_jar: Path
    deck_dir: Optional[Path] = None  # optional: point CLI to the exact directory with -D
    matches: Optional[int] = 3
    games: Optional[int] = None
    format_name: str = "constructed"
    quiet: bool = True
    jvm_args: Optional[List[str]] = None


class ForgeSimRunner:
    """Invoke Forge in headless 'sim' mode, and parse winners robustly."""

    def __init__(self, cfg: ForgeSimConfig):
        self.cfg = cfg

    def run(self, deck_files: List[Path], log_file: Path) -> Dict:
        # Pass filenames; Forge looks in user deck dir or the -D directory if provided
        deck_args = [f.name for f in deck_files]

        cmd: List[str] = [self.cfg.java_bin]
        if self.cfg.jvm_args:
            cmd.extend(self.cfg.jvm_args)
        cmd += [
            "-jar", str(self.cfg.forge_jar),
            "sim",
            "-d", *deck_args,
            "-f", self.cfg.format_name,
        ]
        if self.cfg.deck_dir:
            cmd += ["-D", str(self.cfg.deck_dir)]
        if self.cfg.matches:
            cmd += ["-m", str(self.cfg.matches)]
        elif self.cfg.games:
            cmd += ["-n", str(self.cfg.games)]
        if self.cfg.quiet:
            cmd += ["-q"]

        proc = subprocess.Popen(
            cmd,
            cwd=self.cfg.forge_jar.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stdout_lines: List[str] = []
        for line in proc.stdout:
            stdout_lines.append(line)
        proc.wait()

        output = "".join(stdout_lines)
        log_file.write_text(output, encoding="utf-8")

        wins = self._parse_wins(output, deck_files)

        result = {
            "command": " ".join(shlex.quote(c) for c in cmd),
            "return_code": proc.returncode,
            "raw_log": str(log_file),
            "wins": wins,  # per deck stem, e.g. {'gpt_5_...': 1, 'claude_...': 2}
        }
        return result

    def _parse_wins(self, output: str, deck_files: List[Path]) -> Dict[str, int]:
        """
        Count game winners by mapping Ai(1)/Ai(2) to the order of -d arguments.
        Prefer 'Game Result: ... has won!' lines; if none found, fall back to
        'Game outcome: ... has won ...' lines.
        """
        # Map Ai index -> deck stem (Ai(1) == first -d deck, etc.)
        index_to_stem = {i + 1: deck_files[i].stem for i in range(min(9, len(deck_files)))}
        wins = {f.stem: 0 for f in deck_files}

        lines = output.splitlines()

        # First pass: precise "Game Result" winners
        found_any = False
        for line in lines:
            m = PAT_GAME_RESULT_WIN.search(line)
            if m:
                found_any = True
                ai_idx = int(m.group(1))
                stem = index_to_stem.get(ai_idx)
                if stem:
                    wins[stem] += 1

        # Fallback: look at "Game outcome" winners if nothing was found
        if not found_any:
            for line in lines:
                m = PAT_OUTCOME_WIN.search(line)
                if m:
                    ai_idx = int(m.group(1))
                    stem = index_to_stem.get(ai_idx)
                    if stem:
                        wins[stem] += 1

        return wins
