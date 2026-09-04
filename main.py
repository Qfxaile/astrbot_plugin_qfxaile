from __future__ import annotations

import asyncio
import random
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.message_components import Image
from astrbot.api.star import Context, Star

from qfxaile.abbreviation import AbbreviationService
from qfxaile.config import PluginSettings
from qfxaile.daily_image import DailyImageService
from qfxaile.onebot import OneBotClient
from qfxaile.recall import RecallService
from qfxaile.request_approval import RequestApprovalService
from qfxaile.scheduler import TaskRegistry
from qfxaile.storage import JsonRequestStore
from qfxaile.wordcloud_service import WordcloudService


class QfxailePlugin(Star):
    """AstrBot event adapter for Qfxaile services."""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.context = context
        self.config = config
        self.settings = PluginSettings(config, base_dir=Path(__file__).parent)
        self.registry = TaskRegistry()
        self.store = JsonRequestStore(
            self.settings.data_dir() / "pending_requests.json"
        )
        self.daily_image = DailyImageService(self.settings, self._send_message)
        self.abbreviation = AbbreviationService(
            str(self.settings.value("nbnhhsh_api_url", "")),
            self.settings.bounded_int("nbnhhsh_timeout_seconds", 30, 1, 300),
        )

    async def _send_message(self, session: str, message: Any) -> None:
        await self.context.send_message(session, message)

    def _admins(self, key: str) -> set[str]:
        return self.settings.admins(key)

    def _is_admin(self, event: AstrMessageEvent, key: str) -> bool:
        return self.settings.is_admin(key, event.get_sender_id())

    @staticmethod
    def _raw_message(raw: Any) -> list[Any]:
        if isinstance(raw, Mapping):
            message = raw.get("message", [])
        else:
            message = getattr(raw, "message", [])
        return message if isinstance(message, list) else []

    @staticmethod
    def _raw(event: AstrMessageEvent) -> Mapping[str, Any]:
        raw = getattr(getattr(event, "message_obj", None), "raw_message", None)
        return raw if isinstance(raw, Mapping) else {}

    @classmethod
    def _get_reply_id(cls, event: AstrMessageEvent) -> str | None:
        raw = cls._raw(event)
        for segment in cls._raw_message(raw):
            if isinstance(segment, Mapping) and segment.get("type") == "reply":
                data = segment.get("data", {})
                if isinstance(data, Mapping) and data.get("id") is not None:
                    return str(data["id"])
        for component in getattr(getattr(event, "message_obj", None), "message", []):
            if component.__class__.__name__.lower() == "reply":
                value = getattr(component, "id", None) or getattr(
                    component, "message_id", None
                )
                if value:
                    return str(value)
        return None

    def _client(
        self, event: AstrMessageEvent | None = None, platform: Any = None
    ) -> OneBotClient:
        bot = getattr(event, "bot", None) if event else getattr(platform, "bot", None)
        return OneBotClient(bot)

    def _get_onebot_platform(self) -> Any:
        platform_id = str(self.settings.value("wordcloud_platform_id", "")).strip()
        if platform_id:
            platform = self.context.get_platform_inst(platform_id)
            if platform:
                return platform
        for item in getattr(self.context.platform_manager, "platform_insts", []):
            if item.meta().name == "aiocqhttp":
                return item
        return None

    def _daily_seconds_until_next_run(self) -> float:
        now = datetime.now()
        target = now.replace(
            hour=self.daily_image.schedule_hour(),
            minute=self.daily_image.schedule_minute(),
            second=0,
            microsecond=0,
        )
        if target <= now:
            target += timedelta(days=1)
        return max((target - now).total_seconds(), 1.0)

    async def _daily_scheduler_loop(self) -> None:
        while True:
            await asyncio.sleep(self._daily_seconds_until_next_run())
            await self.daily_image.send_scheduled(
                None, lambda path: MessageChain([Image.fromFileSystem(str(path))])
            )

    async def _wordcloud_scheduler_loop(self) -> None:
        while True:
            now = datetime.now()
            target = now.replace(
                hour=self.settings.bounded_int("wordcloud_schedule_hour", 22, 0, 23),
                minute=self.settings.bounded_int("wordcloud_schedule_minute", 0, 0, 59),
                second=0,
                microsecond=0,
            )
            if target <= now:
                target += timedelta(days=1)
            await asyncio.sleep(max((target - now).total_seconds(), 1.0))
            groups = self.settings.string_list("wordcloud_scheduled_groups")
            platform = self._get_onebot_platform()
            if groups and not platform:
                logger.warning("未找到 OneBot 平台实例，无法自动发送词云。")
                continue
            if groups:
                platform_id = platform.meta().id
                sessions = [
                    f"{platform_id}:GroupMessage:{group_id}" for group_id in groups
                ]
            else:
                sessions = self.settings.string_list("wordcloud_scheduled_sessions")
                groups = [
                    parts[2]
                    for session in sessions
                    if len(parts := session.split(":", 2)) == 3
                ]
            for index, group_id in enumerate(groups):
                if index >= len(sessions) or not sessions[index]:
                    continue
                try:
                    service = WordcloudService(
                        self._client(platform=platform), self.settings
                    )
                    chain = MessageChain(
                        await service.build(
                            str(group_id), datetime.now().strftime("%Y-%m-%d")
                        )
                    )
                    await self.context.send_message(sessions[index], chain)
                except Exception as exc:
                    logger.warning(f"自动发送词云失败 group={group_id}: {exc}")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_request_event(self, event: AstrMessageEvent):
        service = RequestApprovalService(self._client(event), self.store, self.settings)
        await service.handle_request(self._raw(event))

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_decision(self, event: AstrMessageEvent):
        decision = event.message_str.strip()
        if decision not in {"同意", "拒绝"}:
            return
        reply_id = self._get_reply_id(event)
        service = RequestApprovalService(self._client(event), self.store, self.settings)
        try:
            result = await service.decide(
                reply_id or "", decision, event.get_sender_id()
            )
        except (PermissionError, LookupError, ValueError) as exc:
            yield event.plain_result(str(exc))
        except Exception as exc:
            logger.warning(f"审批申请失败: {exc}")
            yield event.plain_result(f"处理失败: {exc}")
        else:
            yield event.plain_result(result)

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_keyword_image(self, event: AstrMessageEvent):
        if not self.daily_image.should_send_keyword(event.message_str, random.random()):
            return
        image_path = self.daily_image.image_path()
        if not image_path.exists():
            yield event.plain_result(f"图片不存在: {image_path}")
            return
        yield event.image_result(str(image_path))

    @filter.on_astrbot_loaded()
    async def on_loaded(self):
        self.registry.start("daily_image", self._daily_scheduler_loop)
        self.registry.start("wordcloud", self._wordcloud_scheduler_loop)
        logger.info("Qfxaile 后台任务已启动。")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_nbnhhsh(self, event: AstrMessageEvent):
        text = event.message_str.strip()
        if not text.startswith(("?", "？")):
            return
        query = text[1:].strip()
        if not query or not query.isascii() or not query.isalnum():
            return
        result = await self.abbreviation.query(query)
        yield event.plain_result(result)

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_recall(self, event: AstrMessageEvent):
        if event.message_str.strip() != "撤回":
            return
        if not self._is_admin(event, "recall_admin_user_ids"):
            yield event.plain_result("你没有权限执行撤回。")
            return
        reply_id = self._get_reply_id(event)
        if not reply_id:
            yield event.plain_result("请回复需要撤回的消息。")
            return
        try:
            await RecallService(self._client(event), self.settings).recall(
                reply_id, str(getattr(event.message_obj, "message_id", "")) or None
            )
        except Exception as exc:
            logger.warning(f"撤回消息失败: {exc}")
            yield event.plain_result(f"撤回消息失败: {exc}")

    @filter.command("wordcloud", alias={"词云", "词云生成"})
    async def wordcloud_command(self, event: AstrMessageEvent):
        group_id = str(event.get_group_id() or "")
        if not group_id:
            yield event.plain_result("词云仅支持群聊。")
            return
        service = WordcloudService(self._client(event), self.settings)
        yield event.chain_result(
            MessageChain(await service.build(group_id, self._get_current_date()))
        )

    @staticmethod
    def _get_current_date() -> str:
        now = datetime.now()
        cutoff = now.replace(hour=22, minute=0, second=0, microsecond=0)
        target = now + timedelta(days=1) if now >= cutoff else now
        return target.strftime("%Y-%m-%d")

    @filter.command("添加词云群组")
    async def add_wordcloud_group(self, event: AstrMessageEvent):
        if not self._is_admin(event, "wordcloud_admin_user_ids"):
            yield event.plain_result("你没有权限管理词云群组。")
            return
        group_id = str(event.get_group_id() or "")
        groups = self.settings.string_list("wordcloud_scheduled_groups")
        if group_id not in groups:
            groups.append(group_id)
            self.config["wordcloud_scheduled_groups"] = groups
            self.config.save_config()
            yield event.plain_result(f"群组 {group_id} 已添加到词云自动发送列表。")
        else:
            yield event.plain_result(f"群组 {group_id} 已经在词云自动发送列表中。")

    @filter.command("删除词云群组")
    async def remove_wordcloud_group(self, event: AstrMessageEvent):
        if not self._is_admin(event, "wordcloud_admin_user_ids"):
            yield event.plain_result("你没有权限管理词云群组。")
            return
        group_id = str(event.get_group_id() or "")
        groups = self.settings.string_list("wordcloud_scheduled_groups")
        if group_id in groups:
            groups.remove(group_id)
            self.config["wordcloud_scheduled_groups"] = groups
            self.config.save_config()
            yield event.plain_result(f"群组 {group_id} 已从词云自动发送列表移除。")
        else:
            yield event.plain_result(f"群组 {group_id} 不在词云自动发送列表中。")

    async def terminate(self):
        await self.registry.stop()
