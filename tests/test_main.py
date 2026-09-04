import main


def test_raw_message_parser_rejects_invalid_shapes():
    assert main.QfxailePlugin._raw_message(None) == []
    assert main.QfxailePlugin._raw_message(object()) == []


def test_plugin_constructor_does_not_create_background_tasks(monkeypatch):
    created = []

    def fake_create_task(coroutine):
        created.append(coroutine)
        coroutine.close()

    monkeypatch.setattr(main.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(main.Star, "__init__", lambda self, context: None)

    plugin = main.QfxailePlugin(object(), {})

    assert plugin.registry.tasks == {}
    assert created == []
