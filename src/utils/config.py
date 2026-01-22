"""
Configuration utilities
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def load_config(config_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load configuration from file"""
    if not config_path:
        # Try default locations
        default_paths = [
            Path("config.json"),
            Path("config.yaml"),
            Path("config.yml"),
            Path("config") / "config.json",
            Path("config") / "config.yaml",
        ]

        for path in default_paths:
            if path.exists():
                config_path = str(path)
                break

        if not config_path:
            return None

    config_path = Path(config_path)
    if not config_path.exists():
        return None

    try:
        if config_path.suffix.lower() in ['.yaml', '.yml']:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            # Assume JSON
            with open(config_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return None