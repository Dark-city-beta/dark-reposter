from __future__ import annotations

import re

PLATFORMS = ("x", "threads", "bluesky", "linkedin", "mastodon")

CONTROL_TAGS = {
    "#noauto",
    "#draft",
    "#manual",
    "#xonly",
    "#nolinkedin",
    "#nothreads",
    "#nobluesky",
    "#nomastodon",
}

NEGATIVE_PLATFORM_TAGS = {
    "x": "#nox",
    "threads": "#nothreads",
    "bluesky": "#nobluesky",
    "linkedin": "#nolinkedin",
    "mastodon": "#nomastodon",
}


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    compact = "\n".join(line for line in lines if line)
    return re.sub(r"[ \t]+", " ", compact).strip()


def extract_tags(text: str) -> set[str]:
    return {tag.lower() for tag in re.findall(r"(?<!\w)#[-_a-zA-Zа-яА-ЯёЁ0-9]+", text)}


def remove_control_tags(text: str) -> str:
    result = text
    for tag in CONTROL_TAGS | set(NEGATIVE_PLATFORM_TAGS.values()):
        result = re.sub(rf"(?<!\w){re.escape(tag)}\b", "", result, flags=re.IGNORECASE)
    return normalize_text(result)


def target_platforms(text: str, configured: list[str]) -> list[str]:
    tags = extract_tags(text)
    if "#noauto" in tags:
        return []
    if "#xonly" in tags:
        return ["x"] if "x" in configured else []

    selected = []
    for platform in configured:
        if NEGATIVE_PLATFORM_TAGS.get(platform) in tags:
            continue
        selected.append(platform)
    return selected


def adapt_for_platform(text: str, platform: str, limit: int) -> str:
    clean = remove_control_tags(text)
    if platform not in PLATFORMS:
        return fit_to_limit(clean, limit)

    if len(clean) <= limit:
        if platform == "linkedin":
            return linkedin_style(clean, limit)
        return clean

    if platform == "linkedin":
        return linkedin_summary(clean, limit)
    if platform in {"x", "bluesky", "mastodon"}:
        return short_summary(clean, limit)
    if platform == "threads":
        return conversational_summary(clean, limit)
    return fit_to_limit(clean, limit)


def linkedin_style(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return linkedin_summary(text, limit)


def split_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?…])\s+|\n+", text)
    return [part.strip(" -•\t") for part in raw if part.strip(" -•\t")]


def extract_hashtags(text: str, reserved: int) -> str:
    tags = []
    for tag in re.findall(r"(?<!\w)#[-_a-zA-Zа-яА-ЯёЁ0-9]+", text):
        if tag.lower() in CONTROL_TAGS:
            continue
        if tag not in tags:
            tags.append(tag)
    result = " ".join(tags[:4])
    return result if len(result) <= reserved else ""


def short_summary(text: str, limit: int) -> str:
    hashtags = extract_hashtags(text, 40)
    reserve = len(hashtags) + (2 if hashtags else 0)
    body_limit = max(40, limit - reserve)

    sentences = split_sentences(re.sub(r"(?<!\w)#[-_a-zA-Zа-яА-ЯёЁ0-9]+", "", text))
    picked: list[str] = []
    for sentence in sentences:
        candidate = " ".join(picked + [sentence])
        if len(candidate) <= body_limit:
            picked.append(sentence)
        if len(picked) >= 2:
            break

    if not picked and sentences:
        picked = [sentences[0]]

    body = " ".join(picked) if picked else text
    body = fit_to_limit(body, body_limit)
    result = f"{body}\n\n{hashtags}".strip() if hashtags else body
    return fit_to_limit(result, limit)


def conversational_summary(text: str, limit: int) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return fit_to_limit(text, limit)

    first = sentences[0]
    if len(sentences) > 1:
        body = first + "\n\n" + " ".join(sentences[1:3])
    else:
        body = first
    return fit_to_limit(body, limit)


def linkedin_summary(text: str, limit: int) -> str:
    sentences = split_sentences(text)
    if len(text) <= limit:
        return text
    if not sentences:
        return fit_to_limit(text, limit)

    intro = sentences[0]
    bullets = []
    for sentence in sentences[1:5]:
        point = fit_to_limit(sentence, 180)
        if point:
            bullets.append(f"• {point}")

    result = intro
    if bullets:
        result += "\n\n" + "\n".join(bullets)
    return fit_to_limit(result, limit)


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
