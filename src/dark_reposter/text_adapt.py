from __future__ import annotations

import re

import os
import httpx
import logging

logger = logging.getLogger(__name__)

PLATFORMS = ("x", "threads", "bluesky", "linkedin", "mastodon")

POSITIVE_PLATFORM_TAGS = {
    "#x": "x",
    "#xonly": "x",
    "#bsky": "bluesky",
    "#bluesky": "bluesky",
    "#masto": "mastodon",
    "#mastodon": "mastodon",
    "#threads": "threads",
    "#in": "linkedin",
    "#linkedin": "linkedin",
}

NEGATIVE_PLATFORM_TAGS = {
    "x": "#nox",
    "threads": "#nothreads",
    "bluesky": "#nobluesky",
    "linkedin": "#nolinkedin",
    "mastodon": "#nomastodon",
}

CONTROL_TAGS = {
    "#noauto",
    "#draft",
    "#manual",
    *POSITIVE_PLATFORM_TAGS.keys(),
    *NEGATIVE_PLATFORM_TAGS.values(),
}


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    compact = "\n".join(line for line in lines if line)
    return re.sub(r"[ \t]+", " ", compact).strip()


def extract_control_tags(text: str) -> set[str]:
    """
    Extracts operational directives (#noauto, #x, #bsky, etc.).
    Only matches tags at the end of the post or on standalone tag lines,
    preventing false positives when control tags are mentioned in explanatory prose.
    """
    control_tags = set()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return control_tags

    for line in reversed(lines[-3:]):
        tokens = line.split()
        if not tokens:
            continue
        if all(t.startswith("#") or t in {",", ";", "|", "/", "-", "•", "*"} for t in tokens):
            for t in tokens:
                clean_tag = re.sub(r"[^\w#]", "", t).lower()
                if clean_tag in CONTROL_TAGS:
                    control_tags.add(clean_tag)
        else:
            for t in reversed(tokens):
                clean_tag = re.sub(r"[^\w#]", "", t).lower()
                if clean_tag in CONTROL_TAGS:
                    control_tags.add(clean_tag)
                else:
                    break
    return control_tags


def extract_tags(text: str) -> set[str]:
    return {tag.lower() for tag in re.findall(r"(?<!\w)#[-_a-zA-Zа-яА-ЯёЁ0-9]+", text)}


def remove_control_tags(text: str) -> str:
    tags = extract_control_tags(text)
    if not tags:
        return text.strip()

    result = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = result.split("\n")
    non_empty = [i for i, l in enumerate(lines) if l.strip()]
    target_indices = set(non_empty[-3:]) if non_empty else set()

    for idx in target_indices:
        line = lines[idx]
        for tag in tags:
            line = re.sub(rf"(?<!\w){re.escape(tag)}\b", "", line, flags=re.IGNORECASE)
        lines[idx] = line

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def target_platforms(text: str, configured: list[str]) -> list[str]:
    tags = extract_control_tags(text)
    if "#noauto" in tags:
        return []

    positive_targets = {POSITIVE_PLATFORM_TAGS[t] for t in tags if t in POSITIVE_PLATFORM_TAGS}
    if positive_targets:
        return [p for p in configured if p in positive_targets and NEGATIVE_PLATFORM_TAGS.get(p) not in tags]

    selected = []
    for platform in configured:
        if NEGATIVE_PLATFORM_TAGS.get(platform) in tags:
            continue
        selected.append(platform)
    return selected


async def adapt_for_platform(text: str, platform: str, limit: int) -> str:
    clean = remove_control_tags(text)
    if len(clean) <= limit:
        return clean

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    if not api_key or not base_url:
        logger.warning("LLM keys not configured, falling back to smart_summary")
        return smart_summary(clean, limit)

    safe_limit = int(limit * 0.90)
    prompt = f"""Rewrite the following text for {platform} social network.
IMPORTANT: You MUST keep the exact same language as the original text. Do not translate it.
Your strict maximum character limit is {safe_limit} characters. You must NOT exceed this limit.
Preserve the core meaning, the most important information, and you MUST keep all URLs.
Preserve hashtags if possible, but drop them if you need space.
Output ONLY the rewritten text, without any explanations."""

    try:
        async with httpx.AsyncClient(proxy=os.getenv("TELEGRAM_PROXY")) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gemini-2.5-flash",
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": clean}
                    ],
                    "temperature": 0.4
                },
                timeout=30.0
            )
            resp.raise_for_status()
            data = resp.json()
            rewritten = data["choices"][0]["message"]["content"].strip()

            if len(rewritten) <= limit:
                return rewritten
            else:
                logger.warning(f"LLM output exceeded limit for {platform}: {len(rewritten)} > {limit}. Falling back to smart_summary on LLM output.")
                return smart_summary(rewritten, limit)
    except Exception as e:
        logger.error(f"LLM rewrite failed: {e}. Falling back to smart_summary.")
        return smart_summary(clean, limit)


def clean_url(url: str) -> str:
    """Strip trailing punctuation that was mistakenly matched as part of the URL."""
    return re.sub(r'[\).,;:!?\'"]+$', '', url)


def extract_urls(text: str) -> list[str]:
    raw_urls = re.findall(r"https?://[^\s<>\"']+", text)
    cleaned = []
    for u in raw_urls:
        c = clean_url(u)
        if c and c not in cleaned:
            cleaned.append(c)
    return cleaned


def extract_hashtags(text: str) -> list[str]:
    tags = []
    seen = set()
    for tag in re.findall(r"(?<!\w)#[-_a-zA-Zа-яА-ЯёЁ0-9]+", text):
        if tag.lower() in CONTROL_TAGS:
            continue
        if tag.lower() not in seen:
            seen.add(tag.lower())
            tags.append(tag)
    return tags


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, preserving sentence-ending punctuation."""
    raw = re.split(r'(?<=[.!?…])\s+', text)
    return [s.strip() for s in raw if s.strip()]


def smart_summary(text: str, limit: int) -> str:
    clean = remove_control_tags(text)
    if len(clean) <= limit:
        return clean

    # Identify primary CTA URL to preserve at the end if the text has to be shortened
    urls = extract_urls(clean)
    tg_urls = [u for u in urls if "t.me/" in u]
    primary_url = tg_urls[0] if tg_urls else (urls[0] if urls else "")

    tags = extract_hashtags(clean)

    # Normalize paragraph blocks
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', clean) if p.strip()]
    if not paragraphs:
        return fit_to_limit(clean, limit)

    cta_part = f"\n\n🔗 {primary_url}" if primary_url else ""
    body_budget = limit - len(cta_part)

    selected_blocks = []
    current_len = 0
    truncated = False

    for i, para in enumerate(paragraphs):
        lines = [l.strip() for l in para.splitlines() if l.strip()]
        is_list = any(l.startswith(("•", "-", "*", "—", "✔", "✅", "⚡", "🔥")) or re.match(r'^\d+[\.\)]', l) for l in lines)

        sep = "\n\n" if selected_blocks else ""
        needed = len(sep) + len(para)

        if current_len + needed <= body_budget:
            selected_blocks.append(para)
            current_len += needed
        else:
            if is_list:
                fitting_items = []
                item_len = current_len
                for item in lines:
                    item_sep = "\n\n" if not selected_blocks and not fitting_items else "\n"
                    if item_len + len(item_sep) + len(item) <= body_budget:
                        fitting_items.append(item)
                        item_len += len(item_sep) + len(item)
                    else:
                        break
                # If all we fit was just a trailing colon header like '🔥 Features:', discard it
                while fitting_items and fitting_items[-1].endswith(":"):
                    fitting_items.pop()

                if fitting_items:
                    selected_blocks.append("\n".join(fitting_items))
                    current_len = item_len
                truncated = True
                break
            else:
                sentences = split_sentences(para)
                fitting_sentences = []
                sent_len = current_len

                for s in sentences:
                    s_sep = "\n\n" if not selected_blocks and not fitting_sentences else " "
                    if sent_len + len(s_sep) + len(s) <= body_budget:
                        fitting_sentences.append(s)
                        sent_len += len(s_sep) + len(s)
                    else:
                        break

                while fitting_sentences and (fitting_sentences[-1].endswith(":") or (len(fitting_sentences[-1]) < 30 and len(fitting_sentences) == 1)):
                    fitting_sentences.pop()

                if fitting_sentences:
                    selected_blocks.append(" ".join(fitting_sentences))
                    current_len = sent_len

                truncated = True
                break

    # Strip any dangling headers at the end of the text
    while selected_blocks and selected_blocks[-1].rstrip().endswith(":"):
        selected_blocks.pop()

    if not selected_blocks:
        cut_budget = limit - len(cta_part) - 1
        cut_text = clean[:max(10, cut_budget)].rsplit(" ", 1)[0].rstrip(" .,:;-—(")
        return f"{cut_text}…{cta_part}".strip()

    body = "\n\n".join(selected_blocks)
    actual_tail = cta_part
    if primary_url and primary_url in body and not truncated:
        actual_tail = ""

    # With remaining space, append as many hashtags as cleanly fit
    remaining_space = limit - len(body) - len(actual_tail)
    chosen_tags = []
    for t in tags[:5]:
        tag_str = (" " if chosen_tags else "\n\n") + t
        if len(tag_str) <= remaining_space:
            chosen_tags.append(t)
            remaining_space -= len(tag_str)
        else:
            break

    tag_part = f"\n\n{' '.join(chosen_tags)}" if chosen_tags else ""
    result = f"{body}{actual_tail}{tag_part}".strip()
    if len(result) > limit:
        return fit_to_limit(clean, limit)
    return result


def fit_to_limit(text: str, limit: int) -> str:
    text = normalize_text(text)
    if len(text) <= limit:
        return text
    if limit <= 1:
        return text[:limit]

    suffix = "…"
    cut_at = max(0, limit - len(suffix))
    shortened = text[:cut_at]
    last_space = shortened.rfind(" ")
    if last_space > int(limit * 0.65):
        shortened = shortened[:last_space]
    return shortened.rstrip(" .,;:-") + suffix

