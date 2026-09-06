from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .config import PluginSettings


class RecallService:
    """Extract reply IDs and delete replied messages through OneBot."""

    def __init__(self, client: Any, settings: PluginSettings) -> None:
        self.client = client
        self.settings = settings

    def reply_id(self, raw: Any, components: Sequence[Any]) -> str | None:
        raw_message = self._message_list(raw)
        for segment in raw_message:
            if isinstance(segment, Mapping) and segment.get("type") == "reply":
                data = segment.get("data")
                if isinstance(data, Mapping) and data.get("id") is not None:
                    return str(data["id"])
        for component in components:
            if component.__class__.__name__.lower() == "reply":
                value = getattr(component, "id", None) or getattr(
                    component, "message_id", None
                )
                if value:
                    return str(value)
        return None

    async def recall(
        self,
        reply_id: str,
        command_message_id: str | None = None,
        *,
        sender_id: str | None = None,
        allow_any: bool = False,
    ) -> None:
        if not allow_any:
            original_sender_id = await self._message_sender(reply_id)
            if not original_sender_id or str(sender_id or "") != original_sender_id:
                raise PermissionError("只能撤回自己发送的消息。")
        await self.client.call("delete_msg", message_id=int(reply_id))
        if (
            self.settings.value("recall.delete_command_message", True)
            and command_message_id
        ):
            await self.client.call("delete_msg", message_id=int(command_message_id))

    async def _message_sender(self, reply_id: str) -> str | None:
        response = await self.client.call("get_msg", message_id=int(reply_id))
        message = (
            response.get("data", response) if isinstance(response, Mapping) else {}
        )
        sender = message.get("sender", message) if isinstance(message, Mapping) else {}
        if not isinstance(sender, Mapping):
            return None
        value = sender.get("user_id")
        return str(value) if value is not None else None

    @staticmethod
    def _message_list(raw: Any) -> list[Any]:
        if isinstance(raw, Mapping):
            value = raw.get("message", [])
        else:
            value = getattr(raw, "message", [])
        return value if isinstance(value, list) else []
