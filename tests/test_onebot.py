import pytest

from qfxaile.onebot import OneBotClient


class ActionBot:
    async def call_action(self, action, **params):
        return {"action": action, **params}


class ApiBot:
    async def call_api(self, action, **params):
        return {"action": action, **params}


@pytest.mark.asyncio
async def test_client_supports_call_action_and_call_api():
    assert await OneBotClient(ActionBot()).call("delete_msg", message_id=1) == {
        "action": "delete_msg",
        "message_id": 1,
    }
    assert await OneBotClient(ApiBot()).call("delete_msg", message_id=2) == {
        "action": "delete_msg",
        "message_id": 2,
    }


@pytest.mark.asyncio
async def test_client_rejects_missing_bot_api():
    with pytest.raises(RuntimeError, match="OneBot"):
        await OneBotClient(object()).call("delete_msg")
