from __future__ import annotations

from dark_reposter.text_adapt import adapt_for_platform


sample = """
Это длинный Telegram-пост про автопостер. В оригинале можно писать свободно, потому что Telegram остаётся главным источником.
Но для X, Bluesky и Mastodon текст нужно сокращать до главных тезисов. Для LinkedIn можно оставить больше контекста и сделать деловой тон.
#test #darkreposter
""".strip()

for platform, limit in {
    "x": 280,
    "threads": 500,
    "bluesky": 300,
    "linkedin": 3000,
    "mastodon": 500,
}.items():
    result = adapt_for_platform(sample, platform, limit)
    print(f"--- {platform} ({len(result)}/{limit}) ---")
    print(result)
