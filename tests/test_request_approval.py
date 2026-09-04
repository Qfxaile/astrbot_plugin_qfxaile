import pytest

from qfxaile.config import PluginSettings
from qfxaile.request_approval import RequestApprovalService


class Client:
    def __init__(self):
        self.calls = []
        self.sent = []

    async def call(self, action, **params):
        self.calls.append((action, params))
        return {}

    async def send_group(self, group_id, message):
        self.sent.append((group_id, message))
        return {"message_id": 99}


class Store:
    def __init__(self):
        self.data = {}

    def load(self):
        return dict(self.data)

    def save(self, data):
        self.data = dict(data)


@pytest.mark.asyncio
async def test_request_service_notifies_and_decides():
    client, store = Client(), Store()
    service = RequestApprovalService(
        client,
        store,
        PluginSettings(
            {
                "agree_notify_group_id": "123",
                "agree_admin_user_ids": ["7"],
                "agree_auto_approve_admin_request": False,
            }
        ),
    )

    await service.handle_request(
        {"post_type": "request", "request_type": "friend", "user_id": 7, "flag": "f"}
    )
    assert "99" in store.data
    assert await service.decide("99", "同意", "7") == "已同意请求 ID: 99"
    assert client.calls[0][0] == "set_friend_add_request"
    assert store.data == {}
