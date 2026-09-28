import re
from urllib.parse import parse_qs, urlparse

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PATH_PREFIXES = ("/embed/", "/shorts/", "/live/", "/v/")


def extract_video_id(url: str) -> str | None:
    """Return the 11-char video id of a YouTube URL, or None if it is not one."""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None

    if parsed.scheme not in ("http", "https"):
        return None

    host = parsed.netloc.lower().removeprefix("www.").removeprefix("m.")

    if host in ("youtu.be",):
        candidate = parsed.path.lstrip("/").split("/")[0]
        return candidate if _VIDEO_ID_RE.match(candidate) else None

    if host not in ("youtube.com", "music.youtube.com", "youtube-nocookie.com"):
        return None

    if parsed.path == "/watch":
        candidates = parse_qs(parsed.query).get("v", [])
        candidate = candidates[0] if candidates else ""
        return candidate if _VIDEO_ID_RE.match(candidate) else None

    for prefix in _PATH_PREFIXES:
        if parsed.path.startswith(prefix):
            candidate = parsed.path[len(prefix) :].split("/")[0]
            return candidate if _VIDEO_ID_RE.match(candidate) else None

    return None


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"
