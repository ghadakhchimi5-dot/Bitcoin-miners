"""Project configuration: locate the project root, read config.yaml, fix seeds."""
from __future__ import annotations

import os
import random
import re
from pathlib import Path

import numpy as np
import yaml


def project_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: cwd) until config.yaml is found.

    Why: notebooks live in notebooks/python/, so relative paths must be resolved
    from the project root, whatever folder the kernel was started in.
    """
    here = Path(start or Path.cwd()).resolve()
    for p in [here, *here.parents]:
        if (p / "config.yaml").exists():
            return p
    raise FileNotFoundError("config.yaml not found in any parent folder")


ROOT = project_root(Path(__file__).parent)


def load_config() -> dict:
    """Read config.yaml (re-read every call so values written by notebook 01 are seen)."""
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def path(key: str) -> Path:
    """Absolute path of a folder declared under `paths:` in config.yaml."""
    p = ROOT / load_config()["paths"][key]
    p.mkdir(parents=True, exist_ok=True)
    return p


def set_seed(seed: int | None = None) -> int:
    """Fix every random generator we use (deep-learning seeds are added in Phase 6)."""
    seed = load_config()["seed"] if seed is None else seed
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    return seed


def update_split(values: dict) -> None:
    """Write split values into the `split:` block of config.yaml.

    Why line-level replacement instead of yaml.dump: it keeps the comments and
    layout of config.yaml intact.
    """
    cfg_path = ROOT / "config.yaml"
    text = cfg_path.read_text(encoding="utf-8")
    head, sep, tail = text.partition("\nsplit:\n")
    block_end = re.search(r"\n(?=\S)", tail)  # next top-level key
    block, rest = (tail[: block_end.start() + 1], tail[block_end.start() + 1 :]) if block_end else (tail, "")
    for k, v in values.items():
        val = f'"{v}"' if isinstance(v, str) else str(v)
        block, n = re.subn(rf"^(\s+{k}:)\s*[^\n#]*", rf"\g<1> {val}", block, flags=re.M)
        if n != 1:
            raise KeyError(f"split.{k} not found in config.yaml")
    cfg_path.write_text(head + sep + block + rest, encoding="utf-8")
