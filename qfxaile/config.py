from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path


class PluginSettings:
    """Provide normalized plugin configuration values.

    Args:
        config: AstrBot configuration mapping.
        plugin_name: Directory name used under AstrBot's plugin data path.
    """

    def __init__(
        self,
        config: Mapping[str, Any],
        plugin_name: str = "astrbot_plugin_qfxaile",
        base_dir: Path | None = None,
    ) -> None:
        self.config = config
        self.plugin_name = plugin_name
        self.base_dir = base_dir

    def value(self, key: str, default: Any = None) -> Any:
        current: Any = self.config
        for part in key.split("."):
            if not isinstance(current, Mapping) or part not in current:
                return default
            current = current[part]
        return current

    def set_value(self, key: str, value: Any) -> None:
        parts = key.split(".")
        current: Any = self.config
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], Mapping):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def admins(self, key: str) -> set[str]:
        value = self.value(key, [])
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            return set()
        return {str(item).strip() for item in value if str(item).strip()}

    def is_admin(self, key: str, user_id: Any) -> bool:
        return str(user_id) in self.admins(key)

    def string_list(self, key: str) -> list[str]:
        value = self.value(key, [])
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def bounded_int(self, key: str, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(self.value(key, default))
        except (TypeError, ValueError):
            value = default
        return max(minimum, min(value, maximum))

    def clock_time(
        self, key: str, default_hour: int, default_minute: int
    ) -> tuple[int, int]:
        value = str(self.value(key, f"{default_hour:02d}:{default_minute:02d}")).strip()
        try:
            hour_text, minute_text = value.split(":", 1)
            hour, minute = int(hour_text), int(minute_text)
        except (TypeError, ValueError):
            return default_hour, default_minute
        return max(0, min(hour, 23)), max(0, min(minute, 59))

    def bounded_float(
        self, key: str, default: float, minimum: float, maximum: float
    ) -> float:
        try:
            value = float(self.value(key, default))
        except (TypeError, ValueError):
            value = default
        return max(minimum, min(value, maximum))

    def data_dir(self) -> Path:
        path = Path(get_astrbot_plugin_data_path()) / self.plugin_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _resolve_path(self, key: str, default: str) -> Path:
        path = Path(str(self.value(key, default)))
        return (
            path
            if path.is_absolute()
            else ((self.base_dir or self.data_dir()) / path).resolve()
        )

    def image_path(self) -> Path:
        return self._resolve_path("daily_image.image_path", "setu.jpg")

    def font_path(self) -> Path:
        return self._resolve_path(
            "wordcloud.font_path", "data/fonts/SourceHanSansSC-Regular.otf"
        )
