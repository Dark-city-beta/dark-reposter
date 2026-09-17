from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def request_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def resolve_with_bot(username: str, token: str) -> int | None:
    query = urllib.parse.urlencode({"chat_id": f"@{username}"})
    url = f"https://api.telegram.org/bot{token}/getChat?{query}"
    data = request_json(url)
    if data.get("ok") and isinstance(data.get("result"), dict):
        chat_id = data["result"].get("id")
        if isinstance(chat_id, int):
            return chat_id
    return None


def inspect_public_page(username: str) -> dict[str, object]:
    url = f"https://t.me/s/{username}"
    with urllib.request.urlopen(url, timeout=20) as response:
        html = response.read().decode("utf-8", "replace")
    posts = re.findall(rf'data-post="{re.escape(username)}/(\d+)"', html)
    return {
        "public_page_ok": True,
        "page_length": len(html),
        "sample_post_ids": posts[:5],
        "has_channel_id_in_html": bool(
            re.search(r"(?:channel_id|chat_id|peer_id|data-peer)[^0-9-]{0,20}-?\d+", html)
        ),
    }


def main() -> int:
    username = (sys.argv[1] if len(sys.argv) > 1 else "dark_city_beta").lstrip("@")
    env = load_env(Path(".env"))
    token = env.get("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")

    if token and "replace_me" not in token:
        try:
            chat_id = resolve_with_bot(username, token)
            if chat_id is not None:
                print(json.dumps({"username": username, "chat_id": chat_id}, ensure_ascii=False))
                return 0
        except Exception as exc:
            print(json.dumps({"username": username, "bot_api_error": str(exc)}, ensure_ascii=False))

    try:
        info = inspect_public_page(username)
    except Exception as exc:
        info = {"public_page_ok": False, "public_page_error": str(exc)}

    print(
        json.dumps(
            {
                "username": username,
                "chat_id": None,
                "reason": "Numeric channel id requires a Telegram bot token with getChat access. The public t.me page does not expose it reliably.",
                **info,
            },
            ensure_ascii=False,
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
