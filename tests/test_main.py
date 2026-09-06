import asyncio
import importlib
import sys
import types
from pathlib import Path

import pytest

plugin_root = Path(__file__).resolve().parents[1]
astrbot_root = plugin_root.parents[1]
sys.path.insert(0, str(astrbot_root))
data_root = astrbot_root / "data"
for package_name, package_path in (
    ("data", data_root),
    ("data.plugins", data_root / "plugins"),
    ("data.plugins.astrbot_plugin_qfxaile", plugin_root),
):
    package = types.ModuleType(package_name)
    package.__path__ = [str(package_path)]
    sys.modules[package_name] = package

main = importlib.import_module("data.plugins.astrbot_plugin_qfxaile.main")


def test_plugin_entrypoint_supports_astrbot_package_import():
    """The plugin entrypoint supports AstrBot package imports."""
    assert main.__package__ == "data.plugins.astrbot_plugin_qfxaile"
    assert main.QfxailePlugin.__name__ == "QfxailePlugin"


def test_raw_message_parser_rejects_invalid_shapes():
    assert main.QfxailePlugin._raw_message(None) == []
    assert main.QfxailePlugin._raw_message(object()) == []


def test_admin_ids_read_astrbot_context_config():
    plugin = main.QfxailePlugin.__new__(main.QfxailePlugin)
    plugin.context = type("Context", (), {"_config": {"admins_id": [7, " 8 ", ""]}})()

    assert plugin._astrbot_admin_ids() == {"7", "8"}


def test_command_text_ignores_reply_mention_prefix():
    event = type("Event", (), {"message_str": " @Nickname(12345) 撤回 "})()

    assert main.QfxailePlugin._command_text(event) == "撤回"


class FakeRecallClient:
    def __init__(self, original_sender_id):
        self.original_sender_id = original_sender_id
        self.calls = []

    async def call(self, action, **params):
        self.calls.append((action, params))
        if action == "get_msg":
            return {"data": {"sender": {"user_id": self.original_sender_id}}}
        return {}


class FakeSettings:
    def __init__(self, values=None):
        self.values = values or {}

    def value(self, key, default):
        return self.values.get(key, default)


class FakeApprovalEvent:
    def __init__(self):
        self.message_str = " @Nickname(12345) 同意 "

    def get_group_id(self):
        return "123"

    def get_sender_id(self):
        return "88"

    def is_admin(self):
        return True

    def plain_result(self, text):
        return text


class FakeRecallEvent:
    def __init__(self, sender_id, is_admin):
        self.message_str = "撤回"
        self.message_obj = type("Message", (), {"message_id": 43})()
        self.sender_id = sender_id
        self.is_admin = lambda: is_admin
        self.results = []
        self.llm_requested = None
        self.stopped = False

    def get_sender_id(self):
        return self.sender_id

    def plain_result(self, text):
        return text

    def should_call_llm(self, value):
        self.llm_requested = value

    def stop_event(self):
        self.stopped = True


@pytest.mark.asyncio
async def test_recall_admin_intercepts_llm_and_deletes_any_message(monkeypatch):
    client = FakeRecallClient("77")
    plugin = main.QfxailePlugin.__new__(main.QfxailePlugin)
    plugin.settings = FakeSettings({"recall.enabled": True})
    plugin._client = lambda event: client
    monkeypatch.setattr(
        main.QfxailePlugin,
        "_get_reply_id",
        lambda self, event: "42",
    )
    event = FakeRecallEvent("88", is_admin=True)

    results = [result async for result in plugin.handle_recall(event)]

    assert results == []
    assert event.llm_requested is True
    assert event.stopped is True
    assert client.calls == [
        ("delete_msg", {"message_id": 42}),
        ("delete_msg", {"message_id": 43}),
    ]


@pytest.mark.asyncio
async def test_recall_non_admin_can_delete_own_message_and_intercepts_llm(monkeypatch):
    client = FakeRecallClient("88")
    plugin = main.QfxailePlugin.__new__(main.QfxailePlugin)
    plugin.settings = FakeSettings({"recall.enabled": True})
    plugin._client = lambda event: client
    monkeypatch.setattr(
        main.QfxailePlugin,
        "_get_reply_id",
        lambda self, event: "42",
    )
    event = FakeRecallEvent("88", is_admin=False)

    results = [result async for result in plugin.handle_recall(event)]

    assert results == []
    assert event.llm_requested is True
    assert event.stopped is True
    assert client.calls == [
        ("get_msg", {"message_id": 42}),
        ("delete_msg", {"message_id": 42}),
        ("delete_msg", {"message_id": 43}),
    ]


@pytest.mark.asyncio
async def test_recall_non_admin_cannot_delete_other_message(monkeypatch):
    client = FakeRecallClient("77")
    plugin = main.QfxailePlugin.__new__(main.QfxailePlugin)
    plugin.settings = FakeSettings({"recall.enabled": True})
    plugin._client = lambda event: client
    monkeypatch.setattr(
        main.QfxailePlugin,
        "_get_reply_id",
        lambda self, event: "42",
    )
    event = FakeRecallEvent("88", is_admin=False)

    results = [result async for result in plugin.handle_recall(event)]

    assert results == ["撤回消息失败: 只能撤回自己发送的消息。"]
    assert event.stopped is True
    assert client.calls == [("get_msg", {"message_id": 42})]


@pytest.mark.asyncio
async def test_quoted_decision_accepts_mention_and_event_admin(monkeypatch):
    plugin = main.QfxailePlugin.__new__(main.QfxailePlugin)
    plugin.settings = FakeSettings({"agree.enabled": True})
    plugin.context = type("Context", (), {"_config": {"admins_id": []}})()
    plugin.store = type("Store", (), {"data": {"42": {"type": "friend"}}})()

    def load(store_self):
        return dict(store_self.data)

    def save(store_self, data):
        store_self.data = dict(data)

    plugin.store.load = lambda: load(plugin.store)
    plugin.store.save = lambda data: save(plugin.store, data)
    plugin._client = lambda event: object()
    event = FakeApprovalEvent()
    monkeypatch.setattr(
        main.QfxailePlugin,
        "_get_reply_id",
        lambda self, event: "42",
    )

    class FakeService:
        def __init__(self, client, store, settings, admin_ids):
            self.store = store

        def can_decide_in_group(self, group_id):
            return group_id == "123"

        async def decide(self, reply_id, decision, sender_id, *, allow):
            assert reply_id == "42"
            assert decision == "同意"
            assert sender_id == "88"
            assert allow is True
            self.store.data.pop(reply_id)
            return "approved"

    monkeypatch.setattr(main, "RequestApprovalService", FakeService)

    results = [result async for result in plugin.handle_decision(event)]

    assert results == ["approved"]
    assert plugin.store.data == {}


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
async def test_plugin_lifecycle_starts_and_stops_background_tasks():
    plugin = main.QfxailePlugin.__new__(main.QfxailePlugin)
    plugin.registry = main.TaskRegistry()

    started = asyncio.Event()

    async def wait_forever():
        started.set()
        await asyncio.Event().wait()

    plugin._daily_scheduler_loop = wait_forever
    plugin._wordcloud_scheduler_loop = wait_forever

    await plugin.initialize()
    await started.wait()

    assert set(plugin.registry.tasks) == {"daily_image", "wordcloud"}

    await plugin.terminate()

    assert plugin.registry.tasks == {}


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
