from qfxaile.config import PluginSettings


def test_settings_normalize_values_and_clamp_bounds(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "qfxaile.config.get_astrbot_plugin_data_path",
        lambda: str(tmp_path / "plugin_data"),
    )
    settings = PluginSettings(
        {
            "agree_admin_user_ids": [123, " 456 ", ""],
            "daily_image_keyword_probability": 2,
            "daily_image_schedule_hour": 99,
            "daily_image_schedule_minute": -4,
        }
    )

    assert settings.admins("agree_admin_user_ids") == {"123", "456"}
    assert settings.bounded_float("daily_image_keyword_probability", 0.15, 0, 1) == 1
    assert settings.bounded_int("daily_image_schedule_hour", 8, 0, 23) == 23
    assert settings.bounded_int("daily_image_schedule_minute", 0, 0, 59) == 0
    assert settings.data_dir() == tmp_path / "plugin_data" / "astrbot_plugin_qfxaile"


def test_settings_resolve_absolute_and_relative_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "qfxaile.config.get_astrbot_plugin_data_path",
        lambda: str(tmp_path / "plugin_data"),
    )
    settings = PluginSettings({"daily_image_image_path": "images/setu.jpg"})

    assert (
        settings.image_path()
        == (
            tmp_path / "plugin_data" / "astrbot_plugin_qfxaile" / "images/setu.jpg"
        ).resolve()
    )
    absolute = tmp_path / "font.otf"
    settings = PluginSettings({"wordcloud_font_path": str(absolute)})
    assert settings.font_path() == absolute
