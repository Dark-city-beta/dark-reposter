from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote

from aiogram import Bot
from aiogram.types import Message

from .models import MediaAsset

logger = logging.getLogger(__name__)


class TelegramMediaStore:
    def __init__(self, public_dir: Path, public_base_url: str | None) -> None:
        self.public_dir = public_dir
        self.public_base_url = public_base_url.rstrip("/") if public_base_url else None
        self.public_dir.mkdir(parents=True, exist_ok=True)

    async def extract_from_messages(self, bot: Bot, messages: list[Message]) -> list[MediaAsset]:
        assets: list[MediaAsset] = []
        for message in messages:
            if not message.photo:
                continue
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)
            suffix = Path(file.file_path or "").suffix or ".jpg"
            name = f"{message.chat.id}_{message.message_id}_{photo.file_unique_id}{suffix}"
            dest = self.public_dir / safe_filename(name)
            await bot.download_file(file.file_path, destination=dest)
            public_url = self.make_public_url(dest)
            if not public_url and file.file_path:
                public_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
            assets.append(
                MediaAsset(
                    local_path=str(dest),
                    public_url=public_url,
                    telegram_file_id=photo.file_id,
                    mime_type="image/jpeg",
                )
            )
        if assets:
            logger.info("Saved %s media files", len(assets))
        return assets

    def make_public_url(self, path: Path) -> str | None:
        if not self.public_base_url:
            return None
        return f"{self.public_base_url}/{quote(path.name)}"


def safe_filename(name: str) -> str:
    allowed = []
    for ch in name:
        if ch.isalnum() or ch in {"-", "_", "."}:
            allowed.append(ch)
        else:
            allowed.append("_")
    return "".join(allowed)
