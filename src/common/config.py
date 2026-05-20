"""Configuration management module."""

import os
import json
from typing import Any, Dict, Optional


class ConfigError(Exception):
    """Raised when a configuration operation is invalid."""
    pass


class Config:
    def __init__(self, config_path: Optional[str] = None):
        self._data: Dict[str, Any] = {}
        if config_path:
            self.load(config_path)
        self._load_env_overrides()

    def load(self, path: str) -> None:
        with open(path) as f:
            self._data = json.load(f)

    def _load_env_overrides(self) -> None:
        prefix = "AO_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower().replace("_", ".")
                self._set_nested(config_key, value, env_override=True)

    def _set_nested(self, key: str, value: Any, env_override: bool = False) -> None:
        parts = key.split(".")
        current = self._data
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            node = current[part]
            if not isinstance(node, dict):
                parent_key = ".".join(parts[:i+1])
                raise ConfigError(
                    f"Cannot set '{key}': '{parent_key}' is a {type(node).__name__}, "
                    f"not a dict. The environment override AO_{key.upper().replace('.', '_')} "
                    f"would replace existing nested config. Use explicit nested keys instead."
                )
            current = node

        # Check that the leaf key is not replacing a dict branch (scalar overwrite)
        if env_override and parts[-1] in current and isinstance(current[parts[-1]], dict):
            raise ConfigError(
                f"Cannot set '{key}' to scalar value: '{key}' is a config branch (dict), "
                f"not a leaf. Environment override AO_{key.upper().replace('.', '_')}={value} "
                f"would silently delete nested settings under '{key}'. "
                f"Use more specific keys like '{key}.<subkey>' instead."
            )

        current[parts[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        parts = key.split(".")
        current = self._data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return default
            else:
                return default
        return current

    def set(self, key: str, value: Any) -> None:
        self._set_nested(key, value)

    def to_dict(self) -> Dict:
        return self._data
