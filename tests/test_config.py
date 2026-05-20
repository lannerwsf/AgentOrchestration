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

    def test_branch_replacement_by_scalar_raises_error_for_env(self, tmp_path, monkeypatch):
        """Setting AO_APP=production when app is a branch should raise ConfigError."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"app": {"name": "test", "port": 8080}}')
        monkeypatch.setenv("AO_APP", "production")
        with pytest.raises(ConfigError, match="Cannot set.*app"):
            Config(str(config_file))

    def test_scalar_set_at_leaf_via_env_is_ok(self, tmp_path, monkeypatch):
        """Setting AO_APP_NAME=foo when app.name is a leaf should work."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"app": {"name": "test", "port": 8080}}')
        monkeypatch.setenv("AO_APP_NAME", "production")
        config = Config(str(config_file))
        assert config.get("app.name") == "production"
        assert config.get("app.port") == 8080

    def test_direct_set_branch_replacement_allowed(self, tmp_path):
        """Direct set() call replacing a branch with scalar is allowed."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"app": {"name": "test", "port": 8080}}')
        config = Config(str(config_file))
        # Direct set allows branch replacement (that's the explicit API)
        config.set("app", "production")
        assert config.get("app") == "production"

    def test_env_override_deep_branch_replacement_raises(self, tmp_path, monkeypatch):
        """Setting AO_A_B=x when a.b is a dict branch should raise."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"a": {"b": {"c": "leaf", "d": "leaf2"}}}')
        monkeypatch.setenv("AO_A_B", "scalar")
        with pytest.raises(ConfigError, match="Cannot set.*a\\.b"):
            Config(str(config_file))

    def test_env_override_deep_leaf_is_ok(self, tmp_path, monkeypatch):
        """Setting AO_A_B_C=value when a.b.c is a leaf should work."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"a": {"b": {"c": "leaf"}}}')
        monkeypatch.setenv("AO_A_B_C", "newvalue")
        config = Config(str(config_file))
        assert config.get("a.b.c") == "newvalue"

    def test_intermediate_scalar_in_path_raises(self):
        """Setting through an intermediate scalar should raise."""
        config = Config()
        config.set("a", "scalar")
        with pytest.raises(ConfigError, match="Cannot set.*a\\.b"):
            config.set("a.b.c", "value")
