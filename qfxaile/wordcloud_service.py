from __future__ import annotations

import asyncio
import re
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import wordcloud
from astrbot.api import logger
from astrbot.api.message_components import Image, Plain

from .config import PluginSettings


class WordcloudService:
    """Handle group history retrieval and wordcloud rendering."""

    def __init__(self, client: Any, settings: PluginSettings) -> None:
        self.client = client
        self.settings = settings

    @staticmethod
    def extract_text(raw_message: Mapping[str, Any]) -> str:
        if not isinstance(raw_message, Mapping):
            return ""
        message_chain = raw_message.get("message", [])
        if isinstance(message_chain, str):
            return message_chain.strip()
        if not isinstance(message_chain, list):
            return ""
        return "".join(
            str(segment.get("data", {}).get("text", ""))
            for segment in message_chain
            if isinstance(segment, Mapping)
            and segment.get("type") == "text"
            and isinstance(segment.get("data"), Mapping)
        ).strip()

    @staticmethod
    def remove_ignored_text(content: str, ignore_texts: set[str]) -> str:
        """从消息中移除配置的忽略短语。"""
        phrases = sorted(
            (phrase.strip() for phrase in ignore_texts if phrase.strip()),
            key=len,
            reverse=True,
        )
        if not phrases:
            return content.strip()
        pattern = "|".join(re.escape(phrase) for phrase in phrases)
        return re.sub(pattern, "", content, flags=re.IGNORECASE).strip()

    async def fetch_messages(
        self, group_id: str, start_time: int, end_time: int
    ) -> list[dict]:
        chunk_size = 100
        exclude_bot_self = bool(self.settings.value("wordcloud.exclude_bot_self", True))
        bot_self_id = str(getattr(getattr(self.client, "bot", None), "self_id", ""))
        all_messages: list[dict] = []
        seen_ids: set[str] = set()
        seen_pages: set[tuple[str, ...]] = set()
        current_anchor: Any = None
        while True:
            fetch_count = chunk_size
            params: dict[str, Any] = {
                "group_id": int(group_id),
                "count": fetch_count,
                "reverseOrder": True,
            }
            if current_anchor is not None:
                params["message_seq"] = current_anchor
            try:
                result = await self.client.call("get_group_msg_history", **params)
            except Exception as exc:
                logger.warning(f"调用 get_group_msg_history 失败: {exc}")
                break
            messages = result.get("messages", []) if isinstance(result, Mapping) else []
            if not isinstance(messages, list) or not messages:
                break
            page_ids = tuple(
                str(item.get("message_id", ""))
                for item in messages
                if isinstance(item, Mapping)
            )
            if page_ids in seen_pages:
                break
            seen_pages.add(page_ids)
            valid_messages = [item for item in messages if isinstance(item, dict)]
            for raw_message in valid_messages:
                msg_id = str(raw_message.get("message_id", ""))
                if msg_id and msg_id in seen_ids:
                    continue
                msg_time = int(raw_message.get("time", 0) or 0)
                if msg_time < start_time or msg_time > end_time:
                    continue
                sender = raw_message.get("sender", {})
                sender_id = (
                    str(sender.get("user_id", ""))
                    if isinstance(sender, Mapping)
                    else ""
                )
                if exclude_bot_self and bot_self_id and sender_id == bot_self_id:
                    continue
                all_messages.append(raw_message)
                if msg_id:
                    seen_ids.add(msg_id)
            earliest = min(
                valid_messages,
                key=lambda item: int(item.get("time", 0) or 0),
                default={},
            )
            earliest_time = int(earliest.get("time", 0) or 0)
            new_anchor = (
                earliest.get("message_seq")
                or earliest.get("real_id")
                or earliest.get("seq")
                or earliest.get("message_id")
            )
            if (
                earliest_time <= start_time
                or new_anchor is None
                or new_anchor == current_anchor
            ):
                break
            current_anchor = new_anchor
            await asyncio.sleep(0.05)
        return sorted(all_messages, key=lambda item: int(item.get("time", 0) or 0))

    async def build(self, group_id: str, daytime: str) -> list[Any]:
        current_date = datetime.strptime(daytime, "%Y-%m-%d")
        start_time = int(
            (current_date - timedelta(days=1)).replace(hour=22, minute=0).timestamp()
        )
        end_time = int(current_date.replace(hour=22, minute=0).timestamp())
        messages = await self.fetch_messages(group_id, start_time, end_time)
        ignore_texts = set(self.settings.string_list("wordcloud.ignore_texts"))
        texts: list[str] = []
        stats: dict[str, int] = {}
        display_names: dict[str, str] = {}
        for raw_message in messages:
            content = self.extract_text(raw_message)
            content = self.remove_ignored_text(content, ignore_texts)
            content = re.sub(r"(http[s]?://\S+|www\.\S+)", "", content).strip()
            if not content or content.isdigit():
                continue
            texts.append(content)
            sender = raw_message.get("sender", {})
            sender = sender if isinstance(sender, Mapping) else {}
            sender_id = str(sender.get("user_id", "未知用户") or "未知用户")
            stats[sender_id] = stats.get(sender_id, 0) + 1
            card = str(sender.get("card", "") or "").strip()
            nickname = str(sender.get("nickname", "") or "").strip()
            if card:
                display_names[sender_id] = card
            elif nickname and not display_names.get(sender_id):
                display_names[sender_id] = nickname
        if not texts:
            return [Plain("没有足够的数据生成词云。")]
        font_path = await self._ensure_font()
        image_path = (
            self.settings.data_dir() / group_id / "wordcloudimg" / f"{daytime}.png"
        )
        image_path.parent.mkdir(parents=True, exist_ok=True)
        cloud = wordcloud.WordCloud(
            width=800,
            height=500,
            background_color="white",
            font_path=str(font_path),
            collocations=False,
            stopwords=ignore_texts,
        )
        cloud.generate_from_text("\n".join(texts))
        cloud.to_file(str(image_path))
        medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
        leaderboard = []
        for index, (user_id, count) in enumerate(
            sorted(stats.items(), key=lambda item: item[1], reverse=True)[:5]
        ):
            name = await self._display_name(
                group_id, user_id, display_names.get(user_id, "")
            )
            leaderboard.append(f"{medals[index]} {name} 贡献值: {count}")
        prev_daytime = (current_date - timedelta(days=1)).strftime("%m-%d")
        summary = (
            f"#WordCloud\n☁️ {daytime} 热门话题\n⏰ {prev_daytime} 22:00截至目前\n"
            f"🗣️ 本群 {len(stats)} 位朋友共贡献 {sum(stats.values())} 条发言\n"
            f"🔍 看下有没有你感兴趣的关键词？\n\n活跃用户排行榜：\n"
            f"{chr(10).join(leaderboard) if leaderboard else '暂无'}\n\n"
            "🎉感谢这些朋友今天的分享!🎉"
        )
        return [Image.fromFileSystem(str(image_path)), Plain(summary)]

    async def _ensure_font(self) -> Path:
        font_path = self.settings.font_path()
        if font_path.exists():
            return font_path
        font_url = str(self.settings.value("wordcloud.font_download_url", "")).strip()
        if not font_url:
            raise RuntimeError(
                f"字体不存在且未配置 wordcloud.font_download_url: {font_path}"
            )
        font_path.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(font_url)
        response.raise_for_status()
        font_path.write_bytes(response.content)
        return font_path

    async def _display_name(self, group_id: str, user_id: str, fallback: str) -> str:
        try:
            info = await self.client.call(
                "get_group_member_info",
                group_id=int(group_id),
                user_id=int(user_id),
                no_cache=False,
            )
            if isinstance(info, Mapping):
                return str(
                    info.get("card") or info.get("nickname") or fallback or user_id
                )
        except Exception:
            pass
        return fallback or user_id
