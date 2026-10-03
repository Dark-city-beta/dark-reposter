from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
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
        try:
            await asyncio.sleep(self.settings.media_group_wait_seconds)
            messages = self._albums.pop(group_id, [])
            self._album_tasks.pop(group_id, None)
            if messages:
                messages.sort(key=lambda item: item.message_id)
                await self._process_messages(messages)
        except Exception:
            logger.exception("Failed to process album group %s", group_id)
            self._albums.pop(group_id, None)
            self._album_tasks.pop(group_id, None)

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
        try:
            await self.bot.send_message(self.settings.telegram_admin_chat_id, "\n".join(lines))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to send admin notification: %s", exc)

    def _is_source_channel(self, message: Message) -> bool:
        expected = (self.settings.telegram_channel_id or "").strip()
        if not expected:
            return True
        if str(message.chat.id) == expected:
            return True
        username = (message.chat.username or "").lower()
        if username:
            clean_expected = expected[1:].lower() if expected.startswith("@") else expected.lower()
            if username == clean_expected:
                return True
        return False


def first_text(messages: list[Message]) -> str:
    for message in messages:
        text = message.text or message.caption or ""
        if text:
            entities = message.entities or message.caption_entities or []
            hidden_links = []
            for ent in entities:
                if ent.type == "text_link" and ent.url and ent.url not in text:
                    hidden_links.append(ent.url)
            if hidden_links:
                text = f"{text}\n\n{' '.join(hidden_links)}"
            return text
    return ""


def format_bot_status(settings: Settings) -> str:
    active_platforms = []
    inactive_platforms = []
    for p in ("x", "bluesky", "mastodon", "threads", "linkedin"):
        cid = settings.buffer_channels.get(p)
        limit = settings.limits.get(p, 0)
        if cid:
            active_platforms.append(f"  • <b>{p.upper()}</b>: 🟢 Активен (ID: <code>{cid}</code>, лимит: {limit} симв.)")
        else:
            inactive_platforms.append(f"  • <b>{p.upper()}</b>: ⚪ Отключён в .env")

    active_text = "\n".join(active_platforms) if active_platforms else "  • Нет активных каналов"
    inactive_text = "\n".join(inactive_platforms) if inactive_platforms else "  • Нет"
    mode_text = "🟢 Боевой (публикация активна)" if not settings.dry_run else "🟡 Тестовый (DRY RUN)"
    chan = settings.telegram_channel_id or "не задан"

    return (
        "🤖 <b>DARK Reposter — Техническое описание и статус</b>\n\n"
        "<b>1. Принцип работы:</b>\n"
        "Автономный сервис репостинга контента из Telegram в соцсети.\n"
        f"• <b>Канал-источник</b>: <code>{chan}</code>\n"
        "• <b>Медиагруппы/альбомы</b>: сбор до 8 сек с объединением медиафайлов\n"
        "• <b>Адаптация текста</b>: умное контекстное сжатие с сохранением абзацев, ссылок и тегов без обрезки слов\n"
        "• <b>Защита от дублей</b>: SQLite дедупликация по chat_id + message_ids\n\n"
        "<b>2. Внешние подключения:</b>\n"
        "• <b>Telegram Bot API & CDN</b> (<code>api.telegram.org</code>): приём постов и передача прямых CDN-ссылок на фото\n"
        f"• <b>Buffer GraphQL API</b> (<code>https://api.buffer.com</code>): единый шлюз публикации (Org: <code>{settings.buffer_organization_id or 'default'}</code>)\n"
        "• <b>Локальная БД</b>: SQLite (<code>data/reposter.sqlite3</code>)\n\n"
        "<b>3. Задействованные соцсети:</b>\n"
        f"<b>Активные:</b>\n{active_text}\n"
        f"<b>Неактивные:</b>\n{inactive_text}\n\n"
        "<b>4. Конфигурация:</b>\n"
        f"• Режим работы: {mode_text}\n"
        f"• Метод отправки: <code>{settings.buffer_mode}</code>\n"
        "• Медиа: Zero-Config Telegram CDN\n\n"
        "<b>5. Управляющие теги:</b>\n"
        "• <code>#x</code>, <code>#bsky</code>, <code>#masto</code>, <code>#threads</code>, <code>#in</code> — публикация только в выбранные сети\n"
        "• <code>#draft</code> — сохранить черновик в БД без отправки в Buffer\n"
        "• <code>#noauto</code> — отменить автоматический репост"
    )


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
    session = AiohttpSession(proxy=settings.telegram_proxy) if settings.telegram_proxy else None
    bot = Bot(settings.telegram_bot_token, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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

    _SUPPORTED_CONTENT = {"text", "photo", "video", "animation", "document", "audio", "voice", "video_note"}
    dp.channel_post.register(source.on_channel_post, F.content_type.in_(_SUPPORTED_CONTENT))

    async def on_edited_channel_post(message: Message) -> None:
        logger.info(
            "Edited channel post %s in chat %s — skipping (Buffer does not support post updates)",
            message.message_id,
            message.chat.id,
        )

    dp.edited_channel_post.register(on_edited_channel_post, F.content_type.in_(_SUPPORTED_CONTENT))

    async def on_private_message(message: Message) -> None:
        await message.answer(format_bot_status(settings), parse_mode=ParseMode.HTML)

    dp.message.register(on_private_message, F.chat.type == "private")

    try:
        await dp.start_polling(bot, allowed_updates=["channel_post", "edited_channel_post", "message"])
    finally:
        await stop_media_server(media_runner)
        await bot.session.close()

