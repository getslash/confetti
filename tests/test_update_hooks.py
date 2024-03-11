def test_update_hook(nested_config, checkpoint):
    @nested_config.on_update
    def callback(config):
        assert nested_config is config
        checkpoint()

    assert not checkpoint.called

    nested_config.root.a.b.value += 1

    assert checkpoint.called
