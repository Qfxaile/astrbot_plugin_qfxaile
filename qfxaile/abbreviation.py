from __future__ import annotations

import re
from typing import Any

import httpx


class AbbreviationService:
    """Query the nbnhhsh abbreviation API asynchronously."""

    def __init__(self, api_url: str, timeout: int, client: Any = None) -> None:
        self.api_url = api_url.strip()
        self.timeout = max(timeout, 1)
        self.client = client

    async def query(self, query: str) -> str:
        query = query.strip()
        if not query or not re.fullmatch(r"[a-zA-Z0-9]+", query):
            return "没有找到这个缩写"
        if not self.api_url:
            return "未配置能不能好好说话 API 地址。"
        try:
            if self.client is not None:
                response = await self.client.post(
                    self.api_url,
                    headers={"accept": "*/*", "content-type": "application/json"},
                    json={"text": query},
                )
                return self._parse_response(query, response)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers={"accept": "*/*", "content-type": "application/json"},
                    json={"text": query},
                )
            return self._parse_response(query, response)
        except Exception as exc:
            return f"请求时发生错误: {exc}"

    @staticmethod
    def _parse_response(query: str, response: Any) -> str:
        if getattr(response, "status_code", 0) != 200:
            return f"请求失败，状态码：{response.status_code}"
        result = response.json()
        if not isinstance(result, list):
            return "没有找到这个缩写"
        translations = [
            str(translation)
            for item in result
            if isinstance(item, dict)
            for translation in item.get("trans", [])
        ]
        return (
            f"{query}: {', '.join(translations)}"
            if translations
            else "没有找到这个缩写"
        )
