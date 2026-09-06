import pytest

from qfxaile.config import PluginSettings
from qfxaile.recall import RecallService


class Client:
    def __init__(self):
        self.calls = []

    async def call(self, action, **params):
        self.calls.append((action, params))
        if action == "get_msg":
            return {"data": {"sender": {"user_id": "42"}}}
        return {}


@pytest.mark.asyncio
async def test_recall_extracts_reply_and_deletes_command_when_enabled():
    client = Client()
    service = RecallService(
        client, PluginSettings({"recall_delete_command_message": True})
    )

    assert (
        service.reply_id({"message": [{"type": "reply", "data": {"id": 42}}]}, [])
        == "42"
    )
    await service.recall("42", "43", sender_id="42")

    assert client.calls == [
        ("get_msg", {"message_id": 42}),
        ("delete_msg", {"message_id": 42}),
        ("delete_msg", {"message_id": 43}),
    ]


@pytest.mark.asyncio
async def test_admin_can_recall_any_message_without_lookup():
    client = Client()
    service = RecallService(client, PluginSettings({}))

    await service.recall("42", "43", allow_any=True)

    assert client.calls == [
        ("delete_msg", {"message_id": 42}),
        ("delete_msg", {"message_id": 43}),
    ]


@pytest.mark.asyncio
async def test_non_admin_can_recall_own_message():
    client = Client()
    service = RecallService(client, PluginSettings({}))

    await service.recall("42", "43", sender_id="42", allow_any=False)

    assert client.calls == [
        ("get_msg", {"message_id": 42}),
        ("delete_msg", {"message_id": 42}),
        ("delete_msg", {"message_id": 43}),
    ]


@pytest.mark.asyncio
async def test_non_admin_cannot_recall_other_message():
    client = Client()

    async def get_other_message(action, **params):
        client.calls.append((action, params))
        return {"data": {"sender": {"user_id": "77"}}}

    client.call = get_other_message
    service = RecallService(client, PluginSettings({}))

    with pytest.raises(PermissionError):
        await service.recall("42", sender_id="88", allow_any=False)
