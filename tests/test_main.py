import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
main = importlib.import_module("data.plugins.astrbot_plugin_qfxaile.main")


def test_plugin_entrypoint_supports_astrbot_package_import():
    """The plugin entrypoint supports AstrBot package imports."""
    assert main.__package__ == "data.plugins.astrbot_plugin_qfxaile"
    assert main.QfxailePlugin.__name__ == "QfxailePlugin"


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


@pytest.mark.asyncio
async def test_wordcloud_command_passes_component_list_to_chain_result(monkeypatch):
    class FakeSettings:
        def value(self, key, default):
            return default

    class FakeEvent:
        message_chain = None

        def get_group_id(self):
            return "123"

        def chain_result(self, chain):
            self.message_chain = chain
            return chain

    class FakeWordcloudService:
        def __init__(self, client, settings):
            pass

        async def build(self, group_id, current_date):
            return ["image", "summary"]

    plugin = main.QfxailePlugin.__new__(main.QfxailePlugin)
    plugin.settings = FakeSettings()
    plugin._client = lambda event: object()
    monkeypatch.setattr(main, "WordcloudService", FakeWordcloudService)
    event = FakeEvent()

    results = [result async for result in plugin.wordcloud_command(event)]

    assert results == [["image", "summary"]]
    assert event.message_chain == ["image", "summary"]
