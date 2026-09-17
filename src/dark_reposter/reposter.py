from __future__ import annotations

import logging

from .config import Settings
from .limits import DEFAULT_MEDIA_LIMITS
from .models import AdaptedPost, PublishResult, TelegramPost
from .publishers import BufferPublisher
from .storage import Storage
from .text_adapt import adapt_for_platform, extract_tags, target_platforms

logger = logging.getLogger(__name__)


class Reposter:
    def __init__(self, settings: Settings, storage: Storage, publisher: BufferPublisher) -> None:
        self.settings = settings
        self.storage = storage
        self.publisher = publisher

    async def handle(self, post: TelegramPost) -> list[PublishResult]:
        tags = extract_tags(post.text)
        if "#noauto" in tags:
            logger.info("Skip post %s due to #noauto", post.message_ids)
            return []

        platforms = target_platforms(post.text, self.settings.enabled_platforms())
        if not platforms:
            logger.info("No target platforms for post %s", post.message_ids)
            return []

        if (
            not self.settings.dry_run
            and post.media
            and self.settings.strict_media
            and any(asset.public_url is None for asset in post.media)
        ):
            err = "Post has media, but PUBLIC_MEDIA_BASE_URL is not configured"
            logger.error(err)
            return [PublishResult(platform=platform, ok=False, error=err) for platform in platforms]

        if "#draft" in tags:
            logger.info("Draft mode: post prepared but not published")
            return [PublishResult(platform=platform, ok=True, remote_id="draft") for platform in platforms]

        post_id = self.storage.save_post(post)
        results: list[PublishResult] = []
        for platform in platforms:
            adapted = self._adapt(post, platform)
            logger.info(
                "Prepared %s version: chars=%s media_urls=%s text=%r",
                platform,
                len(adapted.text),
                len(adapted.media_urls),
                adapted.text[:500],
            )
            result = await self.publisher.publish(adapted)
            self.storage.save_publication(post_id, adapted, result)
            results.append(result)
        return results

    def _adapt(self, post: TelegramPost, platform: str) -> AdaptedPost:
        limit = self.settings.limits[platform]
        media_limit = DEFAULT_MEDIA_LIMITS[platform]
        media_urls = [asset.public_url for asset in post.media if asset.public_url]
        media_urls = media_urls[:media_limit]
        return AdaptedPost(
            platform=platform,
            text=adapt_for_platform(post.text, platform, limit),
            media_urls=media_urls,
        )
