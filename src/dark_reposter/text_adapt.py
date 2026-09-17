from __future__ import annotations

import re

PLATFORMS = ("x", "threads", "bluesky", "linkedin", "mastodon")

CONTROL_TAGS = {
    "#noauto",
    "#draft",
    "#manual",
    "#xonly",
    "#nox",
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
    result = text.replace("\r\n", "\n").replace("\r", "\n")
    for tag in CONTROL_TAGS:
        result = re.sub(rf"(?<!\w){re.escape(tag)}\b", "", result, flags=re.IGNORECASE)
    lines = [line.strip() for line in result.split("\n")]
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def target_platforms(text: str, configured: list[str]) -> list[str]:
    tags = extract_tags(text)
    if "#noauto" in tags or "#draft" in tags:
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
    if len(clean) <= limit:
        return clean

    return smart_summary(clean, limit)


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


def smart_summary(text: str, limit: int) -> str:
    urls = re.findall(r"https?://[^\s]+", text)
    primary_url = urls[0] if urls else ""

    tags = extract_hashtags(text)

    body_text = text
    if primary_url:
        body_text = body_text.replace(primary_url, "").strip()
    for t in tags:
        body_text = re.sub(rf"(?<!\w){re.escape(t)}\b", "", body_text).strip()

    raw_lines = [
        l.strip()
        for l in body_text.splitlines()
        if l.strip() and l.strip() not in {"⭐️ GitHub:", "GitHub:", "⭐️", "🔗", "Link:", "P.S."}
    ]
    if not raw_lines:
        return fit_to_limit(text, limit)

    header = raw_lines[0]
    subsequent = raw_lines[1:]

    link_part = f"\n\n🔗 {primary_url}" if primary_url else ""

    best_candidate = ""
    for max_tags in (3, 2, 1, 0):
        selected_tags = tags[:max_tags]
        tag_part = f"\n\n{' '.join(selected_tags)}" if selected_tags else ""
        fixed_len = len(link_part) + len(tag_part)
        budget = limit - fixed_len

        if budget < len(header):
            continue

        body_elements = [header]
        cur_len = len(header)

        for line in subsequent:
            is_section_hdr = line.endswith(":") or line.startswith(("⚡️", "🔥", "📌", "✨"))
            if is_section_hdr:
                continue

            sep = "\n" if line.startswith(("•", "-", "*")) else "\n\n"
            if cur_len + len(sep) + len(line) <= budget:
                body_elements.append(line)
                cur_len += len(sep) + len(line)
            else:
                sentences = re.split(r"(?<=[.!?…])\s+", line)
                for s in sentences:
                    s_sep = "\n\n"
                    if cur_len + len(s_sep) + len(s) <= budget:
                        body_elements.append(s)
                        cur_len += len(s_sep) + len(s)

        body_str = ""
        for i, elem in enumerate(body_elements):
            if i == 0:
                body_str = elem
            elif elem.startswith(("•", "-", "*")):
                body_str += "\n" + elem
            else:
                body_str += "\n\n" + elem

        candidate = f"{body_str}{link_part}{tag_part}".strip()
        if len(candidate) <= limit:
            best_candidate = candidate
            break

    if not best_candidate:
        cut = max(0, limit - len(link_part) - 4)
        best_candidate = f"{header[:cut]}…{link_part}".strip()

    return best_candidate


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
