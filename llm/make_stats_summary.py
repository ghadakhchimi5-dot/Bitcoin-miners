"""Regenerate llm/stats_summary.md from results/ (run from anywhere: python llm/make_stats_summary.py).

Why a script and not hand-written numbers: every figure given to the LLM must come from executed output,
so the comparison 'human vs LLM' can check the LLM's claims against a single, reproducible source.
"""
import sys
import warnings
from pathlib import Path

ROOT = next(p for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents] if (p / "config.yaml").exists())
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore", category=FutureWarning)

from src import llm_summary  # noqa: E402

if __name__ == "__main__":
    print("written:", llm_summary.build())
