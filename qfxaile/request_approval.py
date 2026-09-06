from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from astrbot.api import logger

from .config import PluginSettings


class RequestApprovalService:
    """Forward and approve OneBot friend or group requests."""

    def __init__(
        self,
        client: Any,
        store: Any,
        settings: PluginSettings,
        admin_ids: Iterable[Any] = (),
    ) -> None:
        self.client = client
        self.store = store
        self.settings = settings
        self.admin_ids = {str(item).strip() for item in admin_ids if str(item).strip()}

    async def handle_request(self, raw: Mapping[str, Any]) -> None:
        if not isinstance(raw, Mapping) or raw.get("post_type") != "request":
            return
        request_type = raw.get("request_type")
        user_id = str(raw.get("user_id", ""))
        if request_type not in {"friend", "group"} or not user_id:
            return
        request_info = {
            "type": request_type,
            "id": user_id,
            "flag": raw.get("flag"),
            "sub_type": raw.get("sub_type"),
            "group_id": raw.get("group_id"),
        }
        if (
            self.settings.value("agree.auto_approve_admin_request", True)
            and user_id in self.admin_ids
        ):
            try:
                await self._approve(request_info, True)
            except Exception as exc:
                logger.warning(f"自动审批申请失败: {exc}")
            return
        notify_group_id = str(self.settings.value("agree.notify_group_id", "")).strip()
        if not notify_group_id:
            return
        admins = self.admin_ids
        text = (
            f"\n用户 {user_id} 请求加好友，请回复本消息并发送“同意”或“拒绝”。"
            if request_type == "friend"
            else f"\n用户 {user_id} 请求加群（群号：{raw.get('group_id')}），请回复本消息并发送“同意”或“拒绝”。"
        )
        try:
            result = await self.client.send_group(
                int(notify_group_id),
                [{"type": "at", "data": {"qq": admin}} for admin in admins]
                + [{"type": "text", "data": {"text": text}}],
            )
            message_id = (
                str(result.get("message_id", "")) if isinstance(result, dict) else ""
            )
        except Exception as exc:
            logger.warning(f"申请转发失败: {exc}")
            return
        if message_id:
            records = self.store.load()
            records[message_id] = request_info
            self.store.save(records)

    async def decide(self, reply_id: str, decision: str, sender_id: str) -> str:
        if decision not in {"同意", "拒绝"}:
            raise ValueError("无效的审批决定")
        if str(sender_id) not in self.admin_ids:
            raise PermissionError("你没有权限审批申请。")
        if not reply_id:
            raise LookupError("请回复相关的申请提醒消息以同意或拒绝请求。")
        records = self.store.load()
        request_info = records.get(reply_id)
        if not request_info:
            raise LookupError("没有找到这条申请记录，可能已经处理过或数据已清理。")
        await self._approve(request_info, decision == "同意")
        records.pop(reply_id, None)
        self.store.save(records)
        return f"已{decision}请求 ID: {reply_id}"

    def can_decide_in_group(self, group_id: Any) -> bool:
        notify_group_id = str(self.settings.value("agree.notify_group_id", "")).strip()
        return bool(notify_group_id) and str(group_id or "") == notify_group_id

    async def _approve(self, request_info: Mapping[str, Any], approve: bool) -> None:
        if request_info.get("type") == "friend":
            await self.client.call(
                "set_friend_add_request", flag=request_info.get("flag"), approve=approve
            )
        elif request_info.get("type") == "group":
            await self.client.call(
                "set_group_add_request",
                flag=request_info.get("flag"),
                sub_type=request_info.get("sub_type") or "add",
                approve=approve,
            )
