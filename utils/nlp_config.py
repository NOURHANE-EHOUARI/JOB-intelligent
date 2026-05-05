# utils/nlp_config.py
import yaml
from pathlib import Path
from typing import Dict

def load_nlp_config(config_path: str = "config/nlp_config.yaml") -> Dict:
    """Charge et valide la configuration NLP depuis le YAML."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config NLP introuvable: {path.resolve()}")
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)