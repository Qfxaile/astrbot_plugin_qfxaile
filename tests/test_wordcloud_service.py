import pytest

from qfxaile.config import PluginSettings
from qfxaile.wordcloud_service import WordcloudService


class Bot:
    self_id = 999


class Client:
    def __init__(self):
        self.bot = Bot()
        self.calls = []

    async def call(self, action, **params):
        self.calls.append((action, params))
        return {
            "messages": [
                {
                    "message_id": 2,
                    "time": 150,
                    "sender": {"user_id": 2},
                    "message": [{"type": "text", "data": {"text": "hello"}}],
                },
                {
                    "message_id": 1,
                    "time": 120,
                    "sender": {"user_id": 1},
                    "message": "world",
                },
            ]
        }


@pytest.mark.asyncio
async def test_fetch_messages_stops_when_page_anchor_has_no_progress(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "qfxaile.config.get_astrbot_plugin_data_path", lambda: str(tmp_path)
    )
    client = Client()
    service = WordcloudService(
        client, PluginSettings({"wordcloud_history_chunk_size": 2})
    )

    messages = await service.fetch_messages("123", 100, 200)

    assert [message["message_id"] for message in messages] == [1, 2]
    assert len(client.calls) == 2


def test_extract_text_supports_string_and_segment_messages():
    assert WordcloudService.extract_text({"message": " hello "}) == "hello"
    assert (
        WordcloudService.extract_text(
            {
                "message": [
                    {"type": "text", "data": {"text": "a"}},
                    {"type": "image", "data": {}},
                ]
            }
        )
        == "a"
    )
