from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import Any

from astrbot.api import logger

from .config import PluginSettings


class DailyImageService:
    """Handle image path resolution, keyword matching and scheduled sends."""

    def __init__(
        self,
        settings: PluginSettings,
        sender: Callable[[str, Any], Awaitable[None] | None],
    ) -> None:
        self.settings = settings
        self.sender = sender

    def image_path(self) -> Path:
        return self.settings.image_path()

    def schedule_hour(self) -> int:
        return self.settings.bounded_int("daily_image_schedule_hour", 8, 0, 23)

    def schedule_minute(self) -> int:
        return self.settings.bounded_int("daily_image_schedule_minute", 0, 0, 59)

    def sessions(self) -> list[str]:
        groups = self.settings.string_list("daily_image_scheduled_groups")
        if groups:
            platform_id = str(
                self.settings.value("daily_image_platform_id", "")
            ).strip()
            if not platform_id:
                return []
            return [f"{platform_id}:GroupMessage:{group_id}" for group_id in groups]
        return self.settings.string_list("daily_image_scheduled_sessions")

    def keyword_matches(self, text: str) -> bool:
        keywords = self.settings.string_list("daily_image_keywords")
        return bool(keywords) and any(keyword in text for keyword in keywords)

    def should_send_keyword(self, text: str, random_value: float) -> bool:
        if not self.keyword_matches(text):
            return False
        probability = self.settings.bounded_float(
            "daily_image_keyword_probability", 0.15, 0.0, 1.0
        )
        return random_value <= probability

    async def send_scheduled(
        self,
        sessions: Sequence[str] | None,
        message_factory: Callable[[Path], Any],
    ) -> None:
        image_path = self.image_path()
        if not image_path.exists():
            logger.warning(f"定时发图图片不存在: {image_path}")
            return
        for session in sessions if sessions is not None else self.sessions():
            try:
                result = self.sender(session, message_factory(image_path))
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                logger.warning(f"定时发图失败 session={session}: {exc}")
