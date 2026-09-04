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
        self, reply_id: str, command_message_id: str | None = None
    ) -> None:
        await self.client.call("delete_msg", message_id=int(reply_id))
        if (
            self.settings.value("recall_delete_command_message", True)
            and command_message_id
        ):
            await self.client.call("delete_msg", message_id=int(command_message_id))

    @staticmethod
    def _message_list(raw: Any) -> list[Any]:
        if isinstance(raw, Mapping):
            value = raw.get("message", [])
        else:
            value = getattr(raw, "message", [])
        return value if isinstance(value, list) else []
