"""Configuration management for APEX-OS Business Platform."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigError(Exception):
    """Configuration error."""


class Config:
    """Hierarchical configuration manager with dot-notation access."""

    _DEFAULTS = {
        "app.name": "apex-os-business-platform",
        "app.version": "0.1.0",
        "app.debug": False,
        "database.host": "localhost",
        "database.port": 5432,
        "database.name": "apex_os_bp",
        "database.user": "apex",
        "database.password": "",
        "api.host": "0.0.0.0",
        "api.port": 8080,
        "api.workers": 4,
        "security.jwt_secret": "",  # Must be set via JWT_SECRET env var
        "security.token_expiry": 3600,
        "logging.level": "INFO",
        "logging.format": "json",
    }

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self._data: Dict[str, Any] = data or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key."""
        if not isinstance(key, str):
            raise ConfigError(f"Key must be a string, got {type(key).__name__}")
        if self._has_key(key):
            return self._get_key(key)
        if key in self._DEFAULTS:
            return self._DEFAULTS[key]
        return default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value by dot-notation key."""
        if not isinstance(key, str):
            raise ConfigError(f"Key must be a string, got {type(key).__name__}")
        self._set_key(key, value)

    def merge(self, other: "Config") -> None:
        """Merge another config into this one."""
        self._data = self._deep_merge(self._data, other._data)

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return dict(self._data)

    def load_file(self, path: str | Path) -> None:
        """Load configuration from JSON or YAML file."""
        path = Path(path)
        if not path.exists():
            raise ConfigError(f"Config file not found: {path}")
        content = path.read_text()
        if path.suffix in (".yaml", ".yml"):
            try:
                import yaml
                data = yaml.safe_load(content)
            except ImportError:
                raise ConfigError("PyYAML required for YAML config files")
        else:
            data = json.loads(content)
        if data:
            self._data = self._deep_merge(self._data, data)

    def _has_key(self, key: str) -> bool:
        parts = key.split(".")
        current = self._data
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        return True

    def _get_key(self, key: str) -> Any:
        parts = key.split(".")
        current = self._data
        for part in parts:
            current = current[part]
        return current

    def _set_key(self, key: str, value: Any) -> None:
        parts = key.split(".")
        current = self._data
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> Dict:
        result = dict(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
