from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


PLATFORMS = ("x", "threads", "bluesky", "linkedin", "mastodon")


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(slots=True)
class Settings:
    telegram_bot_token: str
    telegram_channel_id: str
    telegram_admin_chat_id: str | None

    buffer_api_key: str
    buffer_organization_id: str
    buffer_mode: str = "shareNow"
    buffer_channels: dict[str, str] = field(default_factory=dict)

    public_media_base_url: str | None = None
    media_public_dir: Path = Path("./data/public/media")
    media_server_host: str = "0.0.0.0"
    media_server_port: int = 8787
    media_group_wait_seconds: int = 8

    dry_run: bool = True
    strict_media: bool = True
    log_level: str = "INFO"
    limits: dict[str, int] = field(default_factory=dict)
    data_dir: Path = Path("./data")

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        channels = {
            "x": os.getenv("BUFFER_CHANNEL_X", "").strip(),
            "threads": os.getenv("BUFFER_CHANNEL_THREADS", "").strip(),
            "bluesky": os.getenv("BUFFER_CHANNEL_BLUESKY", "").strip(),
            "linkedin": os.getenv("BUFFER_CHANNEL_LINKEDIN", "").strip(),
            "mastodon": os.getenv("BUFFER_CHANNEL_MASTODON", "").strip(),
        }

        limits = {
            "x": _int("LIMIT_X", 280),
            "threads": _int("LIMIT_THREADS", 500),
            "bluesky": _int("LIMIT_BLUESKY", 300),
            "linkedin": _int("LIMIT_LINKEDIN", 3000),
            "mastodon": _int("LIMIT_MASTODON", 500),
        }

        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_channel_id=os.getenv("TELEGRAM_CHANNEL_ID", "").strip(),
            telegram_admin_chat_id=os.getenv("TELEGRAM_ADMIN_CHAT_ID", "").strip() or None,
            buffer_api_key=os.getenv("BUFFER_API_KEY", "").strip(),
            buffer_organization_id=os.getenv("BUFFER_ORGANIZATION_ID", "").strip(),
            buffer_mode=os.getenv("BUFFER_MODE", "shareNow").strip() or "shareNow",
            buffer_channels=channels,
            public_media_base_url=(os.getenv("PUBLIC_MEDIA_BASE_URL", "").strip().rstrip("/") or None),
            media_public_dir=Path(os.getenv("MEDIA_PUBLIC_DIR", "./data/public/media")),
            media_server_host=os.getenv("MEDIA_SERVER_HOST", "0.0.0.0").strip(),
            media_server_port=_int("MEDIA_SERVER_PORT", 8787),
            media_group_wait_seconds=_int("MEDIA_GROUP_WAIT_SECONDS", 8),
            dry_run=_bool("DRY_RUN", True),
            strict_media=_bool("STRICT_MEDIA", True),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
            limits=limits,
        )

    def validate_for_runtime(self) -> None:
        missing = []
        if is_placeholder(self.telegram_bot_token):
            missing.append("TELEGRAM_BOT_TOKEN")
        if is_placeholder(self.telegram_channel_id):
            missing.append("TELEGRAM_CHANNEL_ID")
        if not self.dry_run and is_placeholder(self.buffer_api_key):
            missing.append("BUFFER_API_KEY")

        configured_channels = [p for p, channel in self.buffer_channels.items() if channel]
        if not self.dry_run and not configured_channels:
            missing.append("BUFFER_CHANNEL_*")

        if missing:
            raise RuntimeError("Missing required settings: " + ", ".join(missing))

    def enabled_platforms(self) -> list[str]:
        configured = [platform for platform in PLATFORMS if self.buffer_channels.get(platform)]
        if self.dry_run and not configured:
            return list(PLATFORMS)
        return configured


def is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip().lower()
    return not normalized or "replace_me" in normalized or normalized in {"@your_channel", "your_channel"}
