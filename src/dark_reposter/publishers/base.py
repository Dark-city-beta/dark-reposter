from __future__ import annotations

from typing import Protocol

from dark_reposter.models import AdaptedPost, PublishResult


class Publisher(Protocol):
    async def publish(self, post: AdaptedPost) -> PublishResult:
        ...
