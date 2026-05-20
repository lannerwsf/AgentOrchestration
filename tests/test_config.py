import pytest
from src.common.config import Config, ConfigError


class TestConfig:
    def test_load_config(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text('{"app": {"name": "test", "port": 8080}}')
        config = Config(str(config_file))
        assert config.get("app.name") == "test"
        assert config.get("app.port") == 8080

    def test_default_value(self):
        config = Config()
        assert config.get("nonexistent.key", "default") == "default"

    def test_set_value(self):
        config = Config()
        config.set("database.host", "localhost")
        assert config.get("database.host") == "localhost"

    def test_nested_set(self):
        config = Config()
        config.set("a.b.c.d", "value")
        assert config.get("a.b.c.d") == "value"

    def test_to_dict(self):
        config = Config()
        config.set("key1", "value1")
        config.set("key2", "value2")
        data = config.to_dict()
        assert data["key1"] == "value1"
        assert data["key2"] == "value2"

    def test_set_nested_on_existing_scalar_raises_error(self):
        """Regression test: setting a nested key where an intermediate
        key exists as a scalar value should raise ConfigError."""
        config = Config()
        config.set("app", "myapp")  # scalar value
        with pytest.raises(ConfigError) as excinfo:
            config.set("app.name", "test")
        assert "intermediate key 'app' already exists as a scalar" in str(excinfo.value)

    def test_set_nested_on_existing_nested_dict_succeeds(self):
        """Setting a nested key where the intermediate key exists as a
        dict should continue to work."""
        config = Config()
        config.set("app.database.host", "localhost")
        # Now set a sibling key - should work fine
        config.set("app.database.port", 5432)
        assert config.get("app.database.host") == "localhost"
        assert config.get("app.database.port") == 5432

    def test_deep_nested_scalar_conflict(self):
        """Deep nesting: conflict at an intermediate depth should still raise."""
        config = Config()
        config.set("a.b.c", "scalar")
        with pytest.raises(ConfigError):
            config.set("a.b.c.d.e", "value")

    def test_branch_sibling_keys_work(self):
        """Sibling keys under the same branch parent should not conflict."""
        config = Config()
        config.set("app.name", "test")
        config.set("app.port", 8080)
        assert config.get("app.name") == "test"
        assert config.get("app.port") == 8080

    def test_env_override_with_existing_scalar_in_file(self, tmp_path, monkeypatch):
        """Regression: environment override on a key path where an intermediate
        key exists as a scalar should raise ConfigError."""
        monkeypatch.setenv("AO_APP_NAME", "overridden")
        config_file = tmp_path / "config.json"
        config_file.write_text('{"app": "myapp"}')
        with pytest.raises(ConfigError):
            Config(str(config_file))
