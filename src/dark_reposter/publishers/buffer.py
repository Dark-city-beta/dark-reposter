from __future__ import annotations

import logging
from typing import Any

import httpx

from dark_reposter.models import AdaptedPost, PublishResult

logger = logging.getLogger(__name__)

BUFFER_ENDPOINT = "https://api.buffer.com"


class BufferPublisher:
    def __init__(
        self,
        api_key: str,
        channel_ids: dict[str, str],
        mode: str = "shareNow",
        dry_run: bool = True,
    ) -> None:
        self.api_key = api_key
        self.channel_ids = {k: v for k, v in channel_ids.items() if v}
        self.mode = mode
        self.dry_run = dry_run

    async def publish(self, post: AdaptedPost) -> PublishResult:
        channel_id = self.channel_ids.get(post.platform)
        if self.dry_run:
            channel_id = channel_id or "dry-run-channel"
            logger.info(
                "DRY RUN %s -> channel=%s chars=%s media=%s text=%r",
                post.platform,
                channel_id,
                len(post.text),
                len(post.media_urls),
                post.text[:500],
            )
            return PublishResult(platform=post.platform, ok=True, remote_id="dry-run")

        if not channel_id:
            return PublishResult(platform=post.platform, ok=False, error="No Buffer channel id configured")

        try:
            data = await self._create_post(channel_id=channel_id, text=post.text, media_urls=post.media_urls)
            remote_id = extract_post_id(data)
            return PublishResult(platform=post.platform, ok=True, remote_id=remote_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Buffer publish failed for %s", post.platform)
            return PublishResult(platform=post.platform, ok=False, error=str(exc))

    async def _create_post(self, channel_id: str, text: str, media_urls: list[str]) -> dict[str, Any]:
        query = """
        mutation CreatePost($input: CreatePostInput!) {
          createPost(input: $input) {
            __typename
            ... on PostActionSuccess {
              post {
                id
                text
                dueAt
                assets {
                  id
                  mimeType
                }
              }
            }
            ... on MutationError {
              message
            }
          }
        }
        """
        variables: dict[str, Any] = {
            "input": {
                "text": text,
                "channelId": channel_id,
                "schedulingType": "automatic",
                "mode": self.mode,
                "assets": [{"image": {"url": url}} for url in media_urls],
            }
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                BUFFER_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables},
            )
            response.raise_for_status()
            payload = response.json()

        if payload.get("errors"):
            raise RuntimeError(payload["errors"])

        result = payload.get("data", {}).get("createPost")
        if not result:
            raise RuntimeError(f"Unexpected Buffer response: {payload}")
        if result.get("__typename") != "PostActionSuccess":
            raise RuntimeError(result.get("message") or f"Buffer error: {result}")
        return result


def extract_post_id(result: dict[str, Any]) -> str | None:
    post = result.get("post") if isinstance(result, dict) else None
    if not isinstance(post, dict):
        return None
    return post.get("id")
