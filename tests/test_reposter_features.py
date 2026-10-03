import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from dark_reposter.config import Settings
from dark_reposter.models import PublishResult, TelegramPost
from dark_reposter.reposter import Reposter
from dark_reposter.storage import Storage
from dark_reposter.text_adapt import target_platforms
from dark_reposter.telegram_app import first_text, format_bot_status


class ReposterFeaturesTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test.sqlite3"
        self.storage = Storage(self.db_path)
        self.settings = Settings(
            telegram_bot_token="fake:token",
            telegram_channel_id="@test",
            telegram_admin_chat_id=None,
            buffer_api_key="fake-key",
            buffer_organization_id="fake-org",
            buffer_channels={"x": "ch_x", "bluesky": "ch_bsky"},
            limits={"x": 280, "bluesky": 300},
            dry_run=True,
        )
        self.publisher = MagicMock()
        self.publisher.publish = AsyncMock(return_value=PublishResult(platform="mock", ok=True, remote_id="test"))
        self.reposter = Reposter(self.settings, self.storage, self.publisher)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_target_platforms_with_draft(self):
        platforms = target_platforms("Some cool post #draft", ["x", "bluesky"])
        self.assertEqual(platforms, ["x", "bluesky"])

    def test_deduplication(self):
        post = TelegramPost(message_ids=[101], chat_id=123, text="Hello world")
        self.assertFalse(self.storage.is_already_processed(123, [101]))

        self.storage.save_post(post)
        self.assertTrue(self.storage.is_already_processed(123, [101]))
        self.assertFalse(self.storage.is_already_processed(123, [102]))

    def test_draft_mode_saves_to_database(self):
        import asyncio

        post = TelegramPost(message_ids=[201], chat_id=123, text="Work in progress post #draft")
        results = asyncio.run(self.reposter.handle(post))

        self.assertEqual(len(results), 2)
        for r in results:
            self.assertTrue(r.ok)
            self.assertEqual(r.remote_id, "draft")

        # Verify post is in storage
        self.assertTrue(self.storage.is_already_processed(123, [201]))

    def test_first_text_extracts_hidden_links(self):
        msg = MagicMock()
        msg.text = "Check out our studio"
        msg.caption = None
        entity = MagicMock()
        entity.type = "text_link"
        entity.url = "https://muzaphoto.ru"
        msg.entities = [entity]
        msg.caption_entities = None

        extracted = first_text([msg])
        self.assertIn("Check out our studio", extracted)
        self.assertIn("https://muzaphoto.ru", extracted)

    def test_format_bot_status(self):
        text = format_bot_status(self.settings)
        self.assertIn("DARK Reposter — Техническое описание", text)
        self.assertIn("Buffer GraphQL API", text)
        self.assertIn("X", text)
        self.assertIn("BLUESKY", text)
        self.assertIn("MASTODON", text)
        self.assertIn("ch_x", text)
        self.assertIn("ch_bsky", text)
        self.assertIn("sqlite3", text)

    def test_dedup_no_false_positive(self):
        """message_id=12 must NOT be treated as duplicate of post [123]."""
        post = TelegramPost(message_ids=[123], chat_id=999, text="test")
        self.storage.save_post(post)

        self.assertFalse(self.storage.is_already_processed(999, [12]))
        self.assertFalse(self.storage.is_already_processed(999, [1]))
        self.assertFalse(self.storage.is_already_processed(999, [23]))
        self.assertTrue(self.storage.is_already_processed(999, [123]))

    def test_dedup_album_order_independence(self):
        """Album [37, 38, 39] must match [39, 38, 37] — order independent."""
        post = TelegramPost(message_ids=[39, 37, 38], chat_id=999, text="album")
        self.storage.save_post(post)

        self.assertTrue(self.storage.is_already_processed(999, [37, 38, 39]))
        self.assertTrue(self.storage.is_already_processed(999, [39, 38, 37]))
        self.assertFalse(self.storage.is_already_processed(999, [37, 38]))

    def test_empty_post_is_skipped(self):
        import asyncio

        empty_post = TelegramPost(message_ids=[500], chat_id=123, text="   ", media=[])
        results = asyncio.run(self.reposter.handle(empty_post))
        self.assertEqual(results, [])

    def test_body_hashtag_not_triggering_noauto(self):
        import asyncio

        post = TelegramPost(
            message_ids=[501],
            chat_id=123,
            text="We discussed the #noauto feature in today's team call.\n\nGreat stuff!",
            media=[],
        )
        results = asyncio.run(self.reposter.handle(post))
        # Should not be skipped, should be processed for both platforms
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()

