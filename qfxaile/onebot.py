from __future__ import annotations

from typing import Any


class OneBotClient:
    """Adapt OneBot client method variants to one async interface."""

    def __init__(self, bot: Any) -> None:
        self.bot = bot

    async def call(self, action: str, **params: Any) -> Any:
        if self.bot and hasattr(self.bot, "call_action"):
            return await self.bot.call_action(action, **params)
        if self.bot and hasattr(self.bot, "call_api"):
            return await self.bot.call_api(action, **params)
        raise RuntimeError("当前事件没有可用的 OneBot 客户端")

    async def send_group(self, group_id: int, message: list[dict]) -> dict:
        if self.bot and hasattr(self.bot, "send_group_msg"):
            return await self.bot.send_group_msg(group_id=group_id, message=message)
        result = await self.call("send_group_msg", group_id=group_id, message=message)
        return result if isinstance(result, dict) else {}
