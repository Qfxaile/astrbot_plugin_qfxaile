import pytest

from qfxaile.config import PluginSettings
from qfxaile.recall import RecallService


class Client:
    def __init__(self):
        self.calls = []

    async def call(self, action, **params):
        self.calls.append((action, params))
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
    await service.recall("42", "43")

    assert client.calls == [
        ("delete_msg", {"message_id": 42}),
        ("delete_msg", {"message_id": 43}),
    ]
