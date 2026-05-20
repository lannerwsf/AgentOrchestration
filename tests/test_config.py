import pytest
from src.common.config import Config


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


class TestConfigGetInt:
    def test_get_int_from_json_number(self):
        config = Config()
        config.set("timeout", 30)
        assert config.get_int("timeout") == 30
        assert isinstance(config.get_int("timeout"), int)

    def test_get_int_from_numeric_string(self):
        config = Config()
        config.set("max_retries", "5")
        assert config.get_int("max_retries") == 5
        assert isinstance(config.get_int("max_retries"), int)

    def test_get_int_with_default(self):
        config = Config()
        assert config.get_int("nonexistent", 42) == 42

    def test_get_int_none_default(self):
        config = Config()
        assert config.get_int("nonexistent") is None

    def test_get_int_invalid_value(self):
        config = Config()
        config.set("name", "not-a-number")
        with pytest.raises(TypeError, match="non-integer"):
            config.get_int("name")

    def test_get_int_zero(self):
        config = Config()
        config.set("count", 0)
        assert config.get_int("count") == 0

    def test_get_int_negative(self):
        config = Config()
        config.set("offset", -1)
        assert config.get_int("offset") == -1

    def test_get_int_float_string(self):
        config = Config()
        config.set("rate", "3.14")
        with pytest.raises(TypeError):
            config.get_int("rate")

    def test_get_int_nested_key(self):
        config = Config()
        config.set("limits.timeout", 60)
        assert config.get_int("limits.timeout") == 60

    def test_get_int_float_number(self):
        config = Config()
        config.set("ratio", 3.14)
        assert config.get_int("ratio") == 3
