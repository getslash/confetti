import pytest
from confetti import Config, Metadata


def test_metadata_access(config):
    assert config.get_config("key1").metadata == {"a": 1, "b": 2}


def test_metadata_access_through_parent(config):
    assert config.get_config("key2").metadata is None


def test_chained_metadata(config):
    assert config.get_config("key3").metadata == {"a": 1, "b": 2}


def test_assigning_does_not_override_metadata(config):
    config.root.key1 = "value3"
    assert config.root.key1 == config.get_config("key1").get_value() == "value3"
    assert config.get_config("key1").metadata == {"a": 1, "b": 2}


def test_assigning_does_not_override_metadata_nested(config):
    config.assign_path("a.b.c", "new_value")
    assert config.get_config("a.b.c").metadata == {"x": 1}


@pytest.fixture
def config():
    return Config(
        {
            "key1": "value1" // Metadata(a=1, b=2),
            "key2": "value2",
            "key3": 1 // Metadata(a=1) // Metadata(b=2),
            "a": {"b": {"c": "nested_value" // Metadata(x=1)}},
        }
    )
