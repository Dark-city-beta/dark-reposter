from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import AdaptedPost, PublishResult, TelegramPost


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    message_ids TEXT NOT NULL,
                    original_text TEXT NOT NULL,
                    media TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS publications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    adapted_text TEXT NOT NULL,
                    media_urls TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    remote_id TEXT,
                    error TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(post_id) REFERENCES posts(id)
                )
                """
            )

    def save_post(self, post: TelegramPost) -> int:
        media = [
            {
                "local_path": item.local_path,
                "public_url": item.public_url,
                "telegram_file_id": item.telegram_file_id,
                "mime_type": item.mime_type,
            }
            for item in post.media
        ]
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO posts(chat_id, message_ids, original_text, media, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(post.chat_id),
                    json.dumps(post.message_ids, ensure_ascii=False),
                    post.text,
                    json.dumps(media, ensure_ascii=False),
                    post.created_at.isoformat(),
                ),
            )
            return int(cur.lastrowid)

    def save_publication(self, post_id: int, adapted: AdaptedPost, result: PublishResult) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO publications(post_id, platform, adapted_text, media_urls, ok, remote_id, error)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post_id,
                    adapted.platform,
                    adapted.text,
                    json.dumps(adapted.media_urls, ensure_ascii=False),
                    1 if result.ok else 0,
                    result.remote_id,
                    result.error,
                ),
            )
