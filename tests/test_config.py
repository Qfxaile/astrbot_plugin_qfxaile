from qfxaile.config import PluginSettings


def test_settings_normalize_values_and_clamp_bounds(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "qfxaile.config.get_astrbot_plugin_data_path",
        lambda: str(tmp_path / "plugin_data"),
    )
    settings = PluginSettings(
        {"daily_image": {"keyword": {"probability": 2}, "schedule_time": "99:-4"}}
    )

    assert settings.bounded_float("daily_image.keyword.probability", 0.15, 0, 1) == 1
    assert settings.clock_time("daily_image.schedule_time", 8, 0) == (23, 0)
    assert settings.data_dir() == tmp_path / "plugin_data" / "astrbot_plugin_qfxaile"


def test_settings_resolve_absolute_and_relative_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "qfxaile.config.get_astrbot_plugin_data_path",
        lambda: str(tmp_path / "plugin_data"),
    )
    settings = PluginSettings({"daily_image": {"image_path": "images/setu.jpg"}})
    assert (
        settings.image_path()
        == (
            tmp_path / "plugin_data" / "astrbot_plugin_qfxaile" / "images/setu.jpg"
        ).resolve()
    )
    absolute = tmp_path / "font.otf"
    settings = PluginSettings({"wordcloud": {"font_path": str(absolute)}})
    assert settings.font_path() == absolute
