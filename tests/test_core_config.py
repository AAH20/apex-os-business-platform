"""Tests for core configuration module."""
import pytest
from apex_os_bp.core.config import Config, ConfigError


class TestConfig:
    """Test configuration management."""

    def test_config_loads_defaults(self):
        """Config loads with default values."""
        config = Config()
        assert config.get("app.name") == "apex-os-business-platform"
        assert config.get("app.version") == "0.1.0"

    def test_config_get_existing_key(self):
        """Config returns value for existing key."""
        config = Config()
        assert config.get("app.name") == "apex-os-business-platform"

    def test_config_get_missing_key_returns_default(self):
        """Config returns default for missing key."""
        config = Config()
        assert config.get("nonexistent.key", "default") == "default"

    def test_config_set_value(self):
        """Config sets and retrieves value."""
        config = Config()
        config.set("test.key", "test_value")
        assert config.get("test.key") == "test_value"

    def test_config_set_nested_key(self):
        """Config handles nested keys."""
        config = Config()
        config.set("database.host", "localhost")
        config.set("database.port", 5432)
        assert config.get("database.host") == "localhost"
        assert config.get("database.port") == 5432

    def test_config_from_dict(self):
        """Config loads from dictionary."""
        data = {"app": {"name": "test-app", "version": "1.0.0"}}
        config = Config(data)
        assert config.get("app.name") == "test-app"
        assert config.get("app.version") == "1.0.0"

    def test_config_invalid_key_raises_error(self):
        """Config raises error for invalid key type."""
        config = Config()
        with pytest.raises(ConfigError):
            config.get(None)

    def test_config_merge(self):
        """Config merges another config."""
        config1 = Config({"app": {"name": "app1"}})
        config2 = Config({"app": {"version": "2.0"}})
        config1.merge(config2)
        assert config1.get("app.name") == "app1"
        assert config1.get("app.version") == "2.0"
