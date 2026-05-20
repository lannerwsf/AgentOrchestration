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
                self._set_nested(config_key, value)

    def _set_nested(self, key: str, value: Any) -> None:
        """Set a nested config value by dotted key path.

        Raises ConfigError if an intermediate key exists as a scalar value
        (i.e., a branch-scalar conflict), because that would silently replace
        branch data with the new value.
        """
        parts = key.split(".")
        current = self._data
        for i, part in enumerate(parts[:-1]):
            if part in current and not isinstance(current[part], dict):
                prefix = ".".join(parts[: i + 1])
                raise ConfigError(
                    f"Cannot set '{key}': intermediate key '{prefix}' already "
                    f"exists as a scalar value (type={type(current[part]).__name__}). "
                    f"Branch-scalar conflicts must be resolved explicitly."
                )
            if part not in current:
                current[part] = {}
            current = current[part]
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
