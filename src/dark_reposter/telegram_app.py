from __future__ import annotations

import asyncio
import logging
import signal
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message

from .config import Settings
from .media import TelegramMediaStore
from .media_server import start_media_server, stop_media_server
from .models import TelegramPost
from .publishers import BufferPublisher
from .reposter import Reposter
from .storage import Storage

logger = logging.getLogger(__name__)


class TelegramSource:
    def __init__(self, settings: Settings, bot: Bot, reposter: Reposter, media_store: TelegramMediaStore) -> None:
        self.settings = settings
        self.bot = bot
        self.reposter = reposter
        self.media_store = media_store
        self._albums: dict[str, list[Message]] = defaultdict(list)
        self._album_tasks: dict[str, asyncio.Task[None]] = {}

    async def on_channel_post(self, message: Message) -> None:
        if not self._is_source_channel(message):
            logger.info("Skip message from unrelated channel %s", message.chat.id)
            return

        if message.media_group_id:
            group_id = str(message.media_group_id)
            self._albums[group_id].append(message)
            if group_id not in self._album_tasks:
                self._album_tasks[group_id] = asyncio.create_task(self._flush_album_later(group_id))
            return

        await self._process_messages([message])

    async def _flush_album_later(self, group_id: str) -> None:
        await asyncio.sleep(self.settings.media_group_wait_seconds)
        messages = self._albums.pop(group_id, [])
        self._album_tasks.pop(group_id, None)
        if messages:
            messages.sort(key=lambda item: item.message_id)
            await self._process_messages(messages)

    async def _process_messages(self, messages: list[Message]) -> None:
        text = first_text(messages)
        if not text:
            text = ""
        media = await self.media_store.extract_from_messages(self.bot, messages)
        post = TelegramPost(
            message_ids=[message.message_id for message in messages],
            chat_id=messages[0].chat.id,
            text=text,
            media=media,
        )
        results = await self.reposter.handle(post)
        await self._notify(post, results)

    async def _notify(self, post: TelegramPost, results) -> None:
        if not self.settings.telegram_admin_chat_id:
            return
        if not results:
            return
        lines = [f"Telegram post {post.message_ids}: repost result"]
        for result in results:
            mark = "✅" if result.ok else "❌"
            detail = result.remote_id or result.error or ""
            lines.append(f"{mark} {result.platform}: {detail}")
        await self.bot.send_message(self.settings.telegram_admin_chat_id, "\n".join(lines))

    def _is_source_channel(self, message: Message) -> bool:
        expected = self.settings.telegram_channel_id
        if not expected:
            return True
        if expected.startswith("@"):
            return (message.chat.username or "").lower() == expected[1:].lower()
        return str(message.chat.id) == expected


def first_text(messages: list[Message]) -> str:
    for message in messages:
        if message.text:
            return message.text
        if message.caption:
            return message.caption
    return ""


async def run() -> None:
    settings = Settings.from_env()
    settings.validate_for_runtime()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    settings.media_public_dir.mkdir(parents=True, exist_ok=True)
    storage = Storage(settings.data_dir / "reposter.sqlite3")
    publisher = BufferPublisher(
        api_key=settings.buffer_api_key,
        channel_ids=settings.buffer_channels,
        mode=settings.buffer_mode,
        dry_run=settings.dry_run,
    )
    bot = Bot(settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    media_store = TelegramMediaStore(settings.media_public_dir, settings.public_media_base_url)
    reposter = Reposter(settings, storage, publisher)
    source = TelegramSource(settings, bot, reposter, media_store)

    media_runner = None
    if settings.public_media_base_url:
        media_runner = await start_media_server(
            directory=settings.media_public_dir,
            host=settings.media_server_host,
            port=settings.media_server_port,
        )
    else:
        logger.info("PUBLIC_MEDIA_BASE_URL is empty; local media server is disabled")

    dp = Dispatcher()
    dp.channel_post.register(source.on_channel_post, F.content_type.in_({"text", "photo"}))

    try:
        await dp.start_polling(bot, allowed_updates=["channel_post", "edited_channel_post"])
    finally:
        await stop_media_server(media_runner)
        await bot.session.close()
