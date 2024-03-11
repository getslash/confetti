from confetti import Config


def test_not_dirty_by_default(nested_config):
    assert not nested_config.is_dirty()
    assert not nested_config["a"].is_dirty()


def test_set_parent(nested_config):
    nested_config.root.value += 1
    assert nested_config.is_dirty()


def test_set_child(nested_config):
    nested_config.root.a.value += 1
    assert nested_config.is_dirty()
    assert nested_config["a"].is_dirty()
    assert not nested_config["a2"].is_dirty()


def test_mark_clean(nested_config):
    nested_config.root.a.value += 1
    nested_config.mark_clean()
    test_not_dirty_by_default(nested_config)


def test_extending_doesnt_count_as_dirty(nested_config):
    nested_config.extend(Config({"new_value": 2}))
    assert not nested_config.is_dirty()
