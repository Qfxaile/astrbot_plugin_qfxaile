import pytest

from qfxaile.config import PluginSettings
from qfxaile.daily_image import DailyImageService


def test_daily_image_clamps_schedule_and_probability(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "qfxaile.config.get_astrbot_plugin_data_path", lambda: str(tmp_path)
    )
    settings = PluginSettings(
        {
            "daily_image_schedule_hour": 99,
            "daily_image_schedule_minute": -1,
            "daily_image_keyword_probability": 2,
            "daily_image_keywords": ["色图"],
        }
    )
    service = DailyImageService(settings, lambda session, message: None)

    assert service.schedule_hour() == 23
    assert service.schedule_minute() == 0
    assert service.should_send_keyword("来张色图", 1.0)
    assert not service.should_send_keyword("普通消息", 0.0)


@pytest.mark.asyncio
async def test_daily_image_skips_missing_file(tmp_path):
    settings = PluginSettings({"daily_image_image_path": str(tmp_path / "missing.jpg")})
    sent = []
    service = DailyImageService(
        settings, lambda session, message: sent.append((session, message))
    )

    await service.send_scheduled(["platform:GroupMessage:1"], lambda path: path)

    assert sent == []
