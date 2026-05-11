"""Конфигурация приложения через Pydantic Settings."""

from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.exceptions import ConfigError


class AppSettings(BaseSettings):
    """Главный объект конфигурации, читается из `.env` + переменных окружения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    anthropic_api_key: SecretStr
    anthropic_model_opus: str = "claude-opus-4-7"
    anthropic_model_haiku: str = "claude-haiku-4-5-20251001"

    # По умолчанию используется вшитый snapshot в репозитории (knowledge_base/data),
    # чтобы работало на cloud-деплое из коробки. Локально можно перезадать через .env
    # на ../cdp_calltouch_kb, если хочется работать с живой базой.
    knowledge_base_path: Path = Path("./knowledge_base/data")
    output_dir: Path = Path("./output")
    sqlite_path: Path = Path("./data/local.db")

    chrome_path: Path | None = None

    target_scenarios_count: int = Field(default=5, ge=3, le=10)
    request_timeout_seconds: int = Field(default=600, ge=30)

    def resolve_paths(self) -> None:
        self.knowledge_base_path = self.knowledge_base_path.expanduser().resolve()
        self.output_dir = self.output_dir.expanduser().resolve()
        self.sqlite_path = self.sqlite_path.expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    def detect_browser(self) -> Path:
        """Найти chrome.exe или msedge.exe для рендера PDF."""
        if self.chrome_path is not None:
            cp = self.chrome_path
            if cp.is_file() and cp.suffix.lower() == ".exe":
                return cp

        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            rf"{Path.home()}\AppData\Local\Google\Chrome\Application\chrome.exe",
            rf"{Path.home()}\AppData\Local\Microsoft\Edge\Application\msedge.exe",
        ]
        for raw in candidates:
            p = Path(raw)
            if p.is_file():
                return p

        for name in ("chrome.exe", "msedge.exe", "chrome", "msedge"):
            found = shutil.which(name)
            if found and Path(found).is_file():
                return Path(found)

        raise ConfigError(
            "Не удалось найти Chrome/Edge для рендера PDF. "
            "Установите Chrome или укажите CHROME_PATH=полный_путь_к_chrome.exe в .env."
        )


_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    global _settings
    if _settings is None:
        _settings = AppSettings()  # type: ignore[call-arg]
        _settings.resolve_paths()
    return _settings
