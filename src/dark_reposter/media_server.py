from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiohttp import web

logger = logging.getLogger(__name__)


async def start_media_server(directory: Path, host: str, port: int) -> web.AppRunner:
    directory.mkdir(parents=True, exist_ok=True)
    app = web.Application()
    app.router.add_static("/media/", path=directory, show_index=False)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    logger.info("Media server is listening on %s:%s and serving %s", host, port, directory)
    return runner


async def stop_media_server(runner: web.AppRunner | None) -> None:
    if runner:
        await runner.cleanup()
        await asyncio.sleep(0)
