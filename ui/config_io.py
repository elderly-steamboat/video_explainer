"""Load and save config.yaml for the settings panel."""
from pathlib import Path

import yaml


def load_config(path: Path = Path("config.yaml")) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def save_config(path: Path, data: dict) -> None:
    Path(path).write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
