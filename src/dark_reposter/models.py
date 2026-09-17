from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class MediaAsset:
    local_path: str
    public_url: str | None
    telegram_file_id: str
    mime_type: str = "image/jpeg"


@dataclass(slots=True)
class TelegramPost:
    message_ids: list[int]
    chat_id: int | str
    text: str
    media: list[MediaAsset] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class AdaptedPost:
    platform: str
    text: str
    media_urls: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PublishResult:
    platform: str
    ok: bool
    remote_id: str | None = None
    error: str | None = None
