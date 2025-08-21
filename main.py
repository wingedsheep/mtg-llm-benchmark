#!/usr/bin/env python3
"""
MTG Agent Benchmark - Main Entry Point

This script orchestrates the complete MTG agent benchmark workflow.
"""

from benchmark_runner import BenchmarkRunner


def main():
    """Main entry point - runs the complete MTG agent benchmark"""
    try:
        runner = BenchmarkRunner()
        runner.run()
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    exit(main())
