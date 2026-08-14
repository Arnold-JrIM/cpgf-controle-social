from typing import Any

import yaml

from .paths import CONFIG_DIR


def load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}
